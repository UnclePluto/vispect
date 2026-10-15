from django.db import migrations

SQL=r'''
REVOKE ALL ON accounts_loginidentity,accounts_loginsessioncontext FROM PUBLIC,vispect_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON accounts_loginidentity,accounts_loginsessioncontext TO vispect_control;
CREATE POLICY identity_metadata_scope ON accounts_account TO vispect_owner
USING (identity_id = NULLIF(current_setting('vispect.identity_id',true),'')::uuid);

CREATE FUNCTION vispect_identity_actor_allowed(p_actor uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.accounts_account a WHERE a.id=p_actor AND a.is_active AND (
   (a.role='tenant_admin' AND a.tenant_id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid)
   OR (a.role='platform_admin' AND a.tenant_id IS NULL AND session_user IN ('vispect_control','vispect_owner'))));
$$;
REVOKE ALL ON FUNCTION vispect_identity_actor_allowed(uuid) FROM PUBLIC;

CREATE FUNCTION vispect_probe_identity(p_actor uuid,p_phone text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
BEGIN
 IF NOT public.vispect_identity_actor_allowed(p_actor) THEN RAISE EXCEPTION 'identity permission denied' USING ERRCODE='42501'; END IF;
 RETURN EXISTS(SELECT 1 FROM public.accounts_loginidentity WHERE phone=p_phone);
END $$;
REVOKE ALL ON FUNCTION vispect_probe_identity(uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vispect_probe_identity(uuid,text) TO vispect_app,vispect_control;

CREATE FUNCTION vispect_ensure_identity(p_actor uuid,p_phone text,p_password text,p_name text)
RETURNS TABLE(identity_id uuid,created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE target uuid;
BEGIN
 IF NOT public.vispect_identity_actor_allowed(p_actor) THEN RAISE EXCEPTION 'identity permission denied' USING ERRCODE='42501'; END IF;
 IF p_phone !~ '^\+861[3-9][0-9]{9}$' THEN RAISE EXCEPTION 'invalid phone' USING ERRCODE='23514'; END IF;
 SELECT id INTO target FROM public.accounts_loginidentity WHERE phone=p_phone;
 IF FOUND THEN RETURN QUERY SELECT target,false; RETURN; END IF;
 IF p_password IS NULL OR p_password='' THEN RAISE EXCEPTION 'initial password required' USING ERRCODE='23514'; END IF;
 INSERT INTO public.accounts_loginidentity(id,phone,name,password,is_active,must_change_password,revision,created_at)
 VALUES(gen_random_uuid(),p_phone,p_name,p_password,true,true,1,now()) ON CONFLICT(phone) DO NOTHING RETURNING id INTO target;
 IF FOUND THEN RETURN QUERY SELECT target,true;
 ELSE SELECT id INTO target FROM public.accounts_loginidentity WHERE phone=p_phone; RETURN QUERY SELECT target,false; END IF;
END $$;
REVOKE ALL ON FUNCTION vispect_ensure_identity(uuid,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vispect_ensure_identity(uuid,text,text,text) TO vispect_app,vispect_control;

CREATE FUNCTION vispect_member_phone(p_actor uuid,p_account uuid) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE result text;
BEGIN
 SELECT COALESCE(i.phone,'') INTO result FROM public.accounts_account a
 LEFT JOIN public.accounts_loginidentity i ON i.id=a.identity_id
 WHERE a.id=p_account AND (
  (a.tenant_id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid AND
   (p_actor=p_account OR public.vispect_identity_actor_allowed(p_actor)))
  OR (session_user IN ('vispect_control','vispect_owner') AND public.vispect_identity_actor_allowed(p_actor)));
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION vispect_member_phone(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vispect_member_phone(uuid,uuid) TO vispect_app,vispect_control;

CREATE FUNCTION vispect_identity_workspaces(p_identity uuid)
RETURNS TABLE(account_id uuid,tenant_id uuid,tenant_name text,tenant_slug text,role text,name text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE previous text := current_setting('vispect.identity_id',true);
BEGIN
 PERFORM set_config('vispect.identity_id',p_identity::text,true);
 RETURN QUERY SELECT a.id,a.tenant_id,t.name::text,t.slug::text,a.role::text,a.name::text
 FROM public.accounts_account a LEFT JOIN public.tenants_tenant t ON t.id=a.tenant_id
 WHERE a.identity_id=p_identity AND a.is_active AND (a.tenant_id IS NULL OR t.enabled)
 ORDER BY t.name NULLS FIRST,a.id;
 PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true);
EXCEPTION WHEN OTHERS THEN PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true); RAISE;
END $$;
REVOKE ALL ON FUNCTION vispect_identity_workspaces(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vispect_identity_workspaces(uuid) TO vispect_control;

CREATE FUNCTION vispect_validate_session_member() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE previous text := current_setting('vispect.identity_id',true);
BEGIN
 IF NEW.active_account_id IS NOT NULL THEN
  PERFORM set_config('vispect.identity_id',NEW.identity_id::text,true);
  IF NOT EXISTS(SELECT 1 FROM public.accounts_account WHERE id=NEW.active_account_id AND identity_id=NEW.identity_id) THEN
   RAISE EXCEPTION 'session membership mismatch' USING ERRCODE='23514';
  END IF;
  PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true);
 END IF;
 RETURN NEW;
EXCEPTION WHEN OTHERS THEN PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true); RAISE;
END $$;
REVOKE ALL ON FUNCTION vispect_validate_session_member() FROM PUBLIC;
CREATE TRIGGER session_member_identity BEFORE INSERT OR UPDATE ON accounts_loginsessioncontext
FOR EACH ROW EXECUTE FUNCTION vispect_validate_session_member();
'''

REVERSE='''
DROP TRIGGER session_member_identity ON accounts_loginsessioncontext;
DROP FUNCTION vispect_validate_session_member();
DROP FUNCTION vispect_identity_workspaces(uuid);
DROP FUNCTION vispect_member_phone(uuid,uuid);
DROP FUNCTION vispect_ensure_identity(uuid,text,text,text);
DROP FUNCTION vispect_probe_identity(uuid,text);
DROP FUNCTION vispect_identity_actor_allowed(uuid);
DROP POLICY identity_metadata_scope ON accounts_account;
'''
class Migration(migrations.Migration):
    dependencies=[('accounts','0004_login_identity')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
