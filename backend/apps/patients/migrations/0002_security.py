from django.db import migrations
from apps.core.rls import apply_tenant_rls
from apps.tenants.quota import quota_trigger_sql
class Migration(migrations.Migration):
    dependencies=[('patients','0001_initial'),('doctors','0002_security')]
    operations=[migrations.RunSQL(apply_tenant_rls('patients_patient')+apply_tenant_rls('patients_patientdoctor')+quota_trigger_sql('patients_patient','patients')+[
        'ALTER TABLE patients_patientdoctor ADD CONSTRAINT patientdoctor_patient_tenant_fk FOREIGN KEY (tenant_id,patient_id) REFERENCES patients_patient(tenant_id,id)',
        'ALTER TABLE patients_patientdoctor ADD CONSTRAINT patientdoctor_doctor_tenant_fk FOREIGN KEY (tenant_id,doctor_id) REFERENCES doctors_doctor(tenant_id,id)',
        'REVOKE DELETE ON patients_patient FROM vispect_app',
    ])]
