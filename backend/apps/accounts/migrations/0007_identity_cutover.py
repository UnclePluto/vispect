from django.db import migrations,models
SQL='''
CREATE FUNCTION vispect_guard_member_identity() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
BEGIN
 IF session_user='vispect_app' AND NEW.tenant_id IS DISTINCT FROM NULLIF(current_setting('vispect.tenant_id',true),'')::uuid THEN
  RAISE EXCEPTION 'tenant context rejected' USING ERRCODE='42501';
 END IF;
 IF session_user IN ('vispect_app','vispect_control') THEN
  IF TG_OP='INSERT' AND NEW.identity_id IS NULL THEN
   RAISE EXCEPTION 'new membership requires identity' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND NEW.identity_id IS DISTINCT FROM OLD.identity_id THEN
   RAISE EXCEPTION 'membership identity is immutable' USING ERRCODE='23514';
  END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION vispect_guard_member_identity() FROM PUBLIC;
CREATE TRIGGER member_identity_guard BEFORE INSERT OR UPDATE ON accounts_account FOR EACH ROW EXECUTE FUNCTION vispect_guard_member_identity();
'''
class Migration(migrations.Migration):
    dependencies=[('accounts','0006_platform_membership_lookup')]
    operations=[migrations.AlterField(model_name='account',name='role',field=models.CharField(max_length=24,choices=[('platform_admin','超级管理员'),('tenant_admin','机构管理员'),('doctor','医生')])),migrations.RunSQL(SQL,'DROP TRIGGER member_identity_guard ON accounts_account; DROP FUNCTION vispect_guard_member_identity();')]
