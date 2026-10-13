from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('core','0002_security')]
    operations=[migrations.RunSQL("CREATE POLICY app_quota_lock ON tenants_tenantquota FOR UPDATE TO vispect_app USING (tenant_id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid) WITH CHECK (tenant_id=NULLIF(current_setting('vispect.tenant_id',true),'')::uuid)")]
