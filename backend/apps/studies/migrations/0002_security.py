from django.db import migrations
from apps.core.rls import apply_tenant_rls
from apps.tenants.quota import quota_trigger_sql
class Migration(migrations.Migration):
    dependencies=[('studies','0001_initial'),('forms','0002_security')]
    operations=[migrations.RunSQL(sum([apply_tenant_rls(t) for t in ['studies_study','studies_studymember','studies_visitdefinition','studies_formbinding']],[])+quota_trigger_sql('studies_study','studies')+[
        'ALTER TABLE studies_study ADD CONSTRAINT study_owner_tenant_fk FOREIGN KEY (tenant_id,owner_id) REFERENCES doctors_doctor(tenant_id,id)',
        'ALTER TABLE studies_studymember ADD CONSTRAINT member_study_tenant_fk FOREIGN KEY (tenant_id,study_id) REFERENCES studies_study(tenant_id,id)',
        'ALTER TABLE studies_studymember ADD CONSTRAINT member_doctor_tenant_fk FOREIGN KEY (tenant_id,doctor_id) REFERENCES doctors_doctor(tenant_id,id)',
        'ALTER TABLE studies_visitdefinition ADD CONSTRAINT stage_study_tenant_fk FOREIGN KEY (tenant_id,study_id) REFERENCES studies_study(tenant_id,id)',
        'ALTER TABLE studies_formbinding ADD CONSTRAINT binding_stage_tenant_fk FOREIGN KEY (tenant_id,stage_id) REFERENCES studies_visitdefinition(tenant_id,id)',
        'ALTER TABLE studies_formbinding ADD CONSTRAINT binding_version_tenant_fk FOREIGN KEY (tenant_id,form_version_id) REFERENCES forms_formversion(tenant_id,id)',
        'REVOKE DELETE ON studies_study FROM vispect_app',
    ])]
