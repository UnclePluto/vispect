from django.db import migrations
from apps.core.rls import apply_tenant_rls

class Migration(migrations.Migration):
    dependencies=[('core','0001_initial'),('tenants','0002_tenantquota'),('accounts','0003_account_rls')]
    operations=[migrations.RunSQL([
        'ALTER TABLE tenants_tenantquota ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE tenants_tenantquota FORCE ROW LEVEL SECURITY',
        "CREATE POLICY app_quota ON tenants_tenantquota FOR SELECT TO vispect_app USING (tenant_id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid)",
        'CREATE POLICY control_quota ON tenants_tenantquota TO vispect_control,vispect_owner USING (true) WITH CHECK (true)',
        'GRANT SELECT ON tenants_tenantquota TO vispect_app',
        'GRANT UPDATE(lock_marker) ON tenants_tenantquota TO vispect_app',
        'GRANT SELECT,INSERT,UPDATE ON tenants_tenantquota TO vispect_control',
        """CREATE FUNCTION vispect_platform_usage() RETURNS TABLE(tenant_id uuid,tenant_name text,doctors bigint,patients bigint,studies bigint)
        LANGUAGE SQL STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
        SELECT t.id,t.name::text,q.doctors_used::bigint,q.patients_used::bigint,q.studies_used::bigint
        FROM public.tenants_tenant t JOIN public.tenants_tenantquota q ON q.tenant_id=t.id $$""",
        'REVOKE ALL ON FUNCTION vispect_platform_usage() FROM PUBLIC',
        'GRANT EXECUTE ON FUNCTION vispect_platform_usage() TO vispect_control',
    ]+sum([apply_tenant_rls(table)+[
        f'CREATE POLICY control_events ON {table} TO vispect_control,vispect_owner USING (tenant_id IS NULL) WITH CHECK (tenant_id IS NULL)',
        f'REVOKE UPDATE,DELETE ON {table} FROM vispect_app',
        f'GRANT SELECT,INSERT ON {table} TO vispect_control',
        f'ALTER TABLE {table} ADD CONSTRAINT {table}_actor_tenant_fk FOREIGN KEY (tenant_id,actor_id) REFERENCES accounts_account(tenant_id,id)',
    ] for table in ['core_auditevent','core_operationreceipt']],[]))]
