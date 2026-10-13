from django.db import migrations
from apps.core.rls import apply_tenant_rls
class Migration(migrations.Migration):
    dependencies=[('followups','0003_answer_answerrevision_and_more'),('studies','0004_formbinding_binding_tenant_id_stage_version_respondent')]
    operations=[migrations.RunSQL(apply_tenant_rls('followups_answer')+apply_tenant_rls('followups_answerrevision')+[
        'ALTER TABLE followups_answer ADD CONSTRAINT answer_visit_stage_fk FOREIGN KEY (tenant_id,visit_id,stage_id) REFERENCES followups_visitinstance(tenant_id,id,stage_id)',
        'ALTER TABLE followups_answer ADD CONSTRAINT answer_binding_stage_version_fk FOREIGN KEY (tenant_id,binding_id,stage_id,form_version_id,respondent) REFERENCES studies_formbinding(tenant_id,id,stage_id,form_version_id,respondent)',
        'ALTER TABLE followups_answer ADD CONSTRAINT answer_recorder_tenant_fk FOREIGN KEY (tenant_id,recorded_by_id) REFERENCES accounts_account(tenant_id,id)',
        "ALTER TABLE followups_answer ADD CONSTRAINT answer_proxy_respondent CHECK (is_proxy = (respondent='patient'))",
        'ALTER TABLE followups_answerrevision ADD CONSTRAINT history_answer_tenant_fk FOREIGN KEY (tenant_id,answer_id) REFERENCES followups_answer(tenant_id,id)',
        'ALTER TABLE followups_answerrevision ADD CONSTRAINT history_actor_tenant_fk FOREIGN KEY (tenant_id,actor_id) REFERENCES accounts_account(tenant_id,id)',
        'ALTER TABLE followups_answerrevision ADD CONSTRAINT history_recorder_tenant_fk FOREIGN KEY (tenant_id,previous_recorded_by_id) REFERENCES accounts_account(tenant_id,id)',
        'REVOKE DELETE ON followups_answer FROM vispect_app',
        'REVOKE UPDATE,DELETE ON followups_answerrevision FROM vispect_app',
        """CREATE FUNCTION vispect_immutable_answer_history() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'answer history is immutable' USING ERRCODE='23514'; END; $$""",
        'CREATE TRIGGER immutable_answer_history BEFORE UPDATE OR DELETE ON followups_answerrevision FOR EACH ROW EXECUTE FUNCTION vispect_immutable_answer_history()',
    ])]
