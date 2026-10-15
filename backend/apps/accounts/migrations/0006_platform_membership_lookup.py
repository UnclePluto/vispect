from django.db import migrations
SQL='''
CREATE FUNCTION vispect_identity_membership(p_actor uuid,p_identity uuid,p_tenant uuid)
RETURNS TABLE(account_id uuid,role text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE previous text := current_setting('vispect.identity_id',true);
BEGIN
 IF session_user NOT IN ('vispect_control','vispect_owner') OR NOT EXISTS(SELECT 1 FROM public.accounts_account actor WHERE actor.id=p_actor AND actor.role='platform_admin' AND actor.is_active AND actor.tenant_id IS NULL) THEN
  RAISE EXCEPTION 'platform permission denied' USING ERRCODE='42501';
 END IF;
 PERFORM set_config('vispect.identity_id',p_identity::text,true);
 RETURN QUERY SELECT a.id,a.role::text FROM public.accounts_account a WHERE a.identity_id=p_identity AND a.tenant_id=p_tenant;
 PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true);
EXCEPTION WHEN OTHERS THEN PERFORM set_config('vispect.identity_id',COALESCE(previous,''),true); RAISE;
END $$;
REVOKE ALL ON FUNCTION vispect_identity_membership(uuid,uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION vispect_identity_membership(uuid,uuid,uuid) TO vispect_control;
'''
class Migration(migrations.Migration):
    dependencies=[('accounts','0005_identity_security')]
    operations=[migrations.RunSQL(SQL,'DROP FUNCTION vispect_identity_membership(uuid,uuid,uuid)')]
