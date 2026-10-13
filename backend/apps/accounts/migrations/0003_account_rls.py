from django.db import migrations
from apps.core.rls import apply_tenant_rls

class Migration(migrations.Migration):
    dependencies=[('accounts','0002_runtime_grants')]
    operations=[migrations.RunSQL(apply_tenant_rls('accounts_account')+[
        "CREATE POLICY control_accounts ON accounts_account TO vispect_control,vispect_owner USING (tenant_id IS NULL OR role='tenant_admin') WITH CHECK (tenant_id IS NULL OR role='tenant_admin')",
        'GRANT SELECT,INSERT,UPDATE,DELETE ON accounts_account TO vispect_control',
        'ALTER TABLE tenants_tenant ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE tenants_tenant FORCE ROW LEVEL SECURITY',
        "CREATE POLICY tenant_metadata ON tenants_tenant FOR SELECT TO vispect_app USING (id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid)",
        'CREATE POLICY control_metadata ON tenants_tenant TO vispect_control,vispect_owner USING (true) WITH CHECK (true)',
        'REVOKE ALL ON django_session FROM vispect_app',
    ])]
