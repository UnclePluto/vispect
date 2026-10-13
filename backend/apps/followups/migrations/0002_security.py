from django.db import migrations
from apps.core.rls import apply_tenant_rls
class Migration(migrations.Migration):
    dependencies=[('followups','0001_initial'),('studies','0003_visitdefinition_stage_tenant_id_study')]
    operations=[migrations.RunSQL(apply_tenant_rls('followups_enrollment')+apply_tenant_rls('followups_visitinstance')+[
        'ALTER TABLE followups_enrollment ADD CONSTRAINT enrollment_study_tenant_fk FOREIGN KEY (tenant_id,study_id) REFERENCES studies_study(tenant_id,id)',
        'ALTER TABLE followups_enrollment ADD CONSTRAINT enrollment_patient_tenant_fk FOREIGN KEY (tenant_id,patient_id) REFERENCES patients_patient(tenant_id,id)',
        'ALTER TABLE followups_enrollment ADD CONSTRAINT enrollment_doctor_tenant_fk FOREIGN KEY (tenant_id,doctor_id) REFERENCES doctors_doctor(tenant_id,id)',
        'ALTER TABLE followups_visitinstance ADD CONSTRAINT visit_enrollment_study_fk FOREIGN KEY (tenant_id,enrollment_id,study_id) REFERENCES followups_enrollment(tenant_id,id,study_id)',
        'ALTER TABLE followups_visitinstance ADD CONSTRAINT visit_stage_study_fk FOREIGN KEY (tenant_id,stage_id,study_id) REFERENCES studies_visitdefinition(tenant_id,id,study_id)',
        'ALTER TABLE followups_enrollment ADD CONSTRAINT current_visit_enrollment_fk FOREIGN KEY (tenant_id,id,current_visit_id) REFERENCES followups_visitinstance(tenant_id,enrollment_id,id)',
        'REVOKE DELETE ON followups_enrollment,followups_visitinstance FROM vispect_app',
        """CREATE FUNCTION vispect_protect_frozen_protocol() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE old_study uuid; new_study uuid;
        BEGIN
          IF TG_TABLE_NAME='studies_visitdefinition' THEN
            IF TG_OP<>'INSERT' THEN old_study:=OLD.study_id; END IF;
            IF TG_OP<>'DELETE' THEN new_study:=NEW.study_id; END IF;
          ELSE
            IF TG_OP<>'INSERT' THEN SELECT study_id INTO old_study FROM studies_visitdefinition WHERE id=OLD.stage_id; END IF;
            IF TG_OP<>'DELETE' THEN SELECT study_id INTO new_study FROM studies_visitdefinition WHERE id=NEW.stage_id; END IF;
          END IF;
          IF EXISTS(SELECT 1 FROM studies_study WHERE id IN (old_study,new_study) AND protocol_frozen) THEN RAISE EXCEPTION 'study protocol is frozen' USING ERRCODE='23514'; END IF;
          IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
        END; $$""",
        'CREATE TRIGGER protect_frozen_stage BEFORE INSERT OR UPDATE OR DELETE ON studies_visitdefinition FOR EACH ROW EXECUTE FUNCTION vispect_protect_frozen_protocol()',
        'CREATE TRIGGER protect_frozen_binding BEFORE INSERT OR UPDATE OR DELETE ON studies_formbinding FOR EACH ROW EXECUTE FUNCTION vispect_protect_frozen_protocol()',
        """CREATE FUNCTION vispect_no_protocol_unfreeze() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.protocol_frozen AND NOT NEW.protocol_frozen THEN RAISE EXCEPTION 'study protocol cannot be unfrozen' USING ERRCODE='23514'; END IF; RETURN NEW; END; $$""",
        'CREATE TRIGGER no_protocol_unfreeze BEFORE UPDATE ON studies_study FOR EACH ROW EXECUTE FUNCTION vispect_no_protocol_unfreeze()',
    ])]
