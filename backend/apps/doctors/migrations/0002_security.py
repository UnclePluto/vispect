from django.db import migrations
from apps.core.rls import apply_tenant_rls
from apps.tenants.quota import quota_trigger_sql

class Migration(migrations.Migration):
    dependencies=[('doctors','0001_initial'),('core','0003_quota_lock_policy')]
    operations=[migrations.RunSQL(apply_tenant_rls('doctors_doctor')+quota_trigger_sql('doctors_doctor','doctors')+[
        'ALTER TABLE doctors_doctor ADD CONSTRAINT doctor_account_tenant_fk FOREIGN KEY (tenant_id,account_id) REFERENCES accounts_account(tenant_id,id)',
        'ALTER TABLE accounts_account ADD CONSTRAINT account_doctor_tenant_fk FOREIGN KEY (tenant_id,doctor_id) REFERENCES doctors_doctor(tenant_id,id)',
        'REVOKE DELETE ON doctors_doctor FROM vispect_app',
    ])]
