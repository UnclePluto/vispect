from django.db import migrations


def backfill_authorship(apps,schema_editor):
    Answer=apps.get_model('followups','Answer');History=apps.get_model('followups','AnswerRevision')
    alias=schema_editor.connection.alias
    schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
    schema_editor.execute('ALTER TABLE followups_answerrevision DISABLE TRIGGER immutable_answer_history')
    try:
        tenant_ids=Answer.objects.using(alias).values_list('tenant_id',flat=True).distinct()
        # FORCE RLS requires tenant scope even for the migration role.
        from django.db import connections
        with connections[alias].cursor() as cursor:
            cursor.execute('SELECT id FROM tenants_tenant');tenant_ids=[r[0] for r in cursor.fetchall()]
            for tenant_id in tenant_ids:
                cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant_id)])
                for answer in Answer.objects.using(alias).filter(tenant_id=tenant_id):
                    history=list(History.objects.using(alias).filter(answer_id=answer.id).order_by('previous_revision'))
                    if answer.status=='submitted':
                        first_id=history[0].previous_recorded_by_id if history else answer.recorded_by_id
                        Answer.objects.using(alias).filter(id=answer.id).update(submitted_by_id=first_id,submission_source='proxy' if answer.respondent=='patient' else 'doctor')
                    for i,item in enumerate(history):
                        after=history[i+1].previous_answers if i+1<len(history) else answer.answers
                        History.objects.using(alias).filter(id=item.id).update(new_answers=after)
            cursor.execute("SELECT set_config('vispect.tenant_id','',true)")
    finally:
        schema_editor.execute('ALTER TABLE followups_answerrevision ENABLE TRIGGER immutable_answer_history')


SQL=[
    'ALTER TABLE followups_answer DROP CONSTRAINT answer_proxy_respondent',
    'ALTER TABLE followups_answer ADD CONSTRAINT answer_recorder_one CHECK (num_nonnulls(recorded_by_id,recorded_by_patient_id)=1)',
    "ALTER TABLE followups_answer ADD CONSTRAINT answer_submission_origin CHECK ((status='draft' AND submission_source IS NULL AND submitted_by_id IS NULL AND submitted_by_patient_id IS NULL) OR (status='submitted' AND ((submission_source='patient' AND respondent='patient' AND NOT is_proxy AND submitted_by_id IS NULL AND submitted_by_patient_id IS NOT NULL) OR (submission_source='proxy' AND respondent='patient' AND is_proxy AND submitted_by_id IS NOT NULL AND submitted_by_patient_id IS NULL) OR (submission_source='doctor' AND respondent='doctor' AND NOT is_proxy AND submitted_by_id IS NOT NULL AND submitted_by_patient_id IS NULL))))",
    "ALTER TABLE followups_answer ADD CONSTRAINT answer_patient_recorder_type CHECK (recorded_by_patient_id IS NULL OR respondent='patient')",
    'ALTER TABLE followups_answerrevision ADD CONSTRAINT history_previous_recorder_one CHECK (num_nonnulls(previous_recorded_by_id,previous_recorded_by_patient_id)=1)',
    r'''CREATE FUNCTION vispect_immutable_submission_origin() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF OLD.status='submitted' AND ROW(OLD.submitted_by_id,OLD.submitted_by_patient_id,OLD.submission_source,OLD.submitted_at,OLD.is_proxy) IS DISTINCT FROM ROW(NEW.submitted_by_id,NEW.submitted_by_patient_id,NEW.submission_source,NEW.submitted_at,NEW.is_proxy) THEN
        RAISE EXCEPTION 'submission origin is immutable' USING ERRCODE='23514';
      END IF; RETURN NEW;
    END $$''',
    'CREATE TRIGGER immutable_submission_origin BEFORE UPDATE ON followups_answer FOR EACH ROW EXECUTE FUNCTION vispect_immutable_submission_origin()',
]
for table,column,target in [('answer','recorded_by_patient','patient_portal_patientloginidentity'),('answer','submitted_by_patient','patient_portal_patientloginidentity'),('answer','submitted_by','accounts_account'),('answerrevision','previous_recorded_by_patient','patient_portal_patientloginidentity')]:
    SQL.append(f'ALTER TABLE followups_{table} ADD CONSTRAINT {table}_{column}_scope_fk FOREIGN KEY (tenant_id,{column}_id) REFERENCES {target}(tenant_id,id)')

class Migration(migrations.Migration):
    dependencies=[('followups','0005_patient_answer_authorship'),('patient_portal','0002_security')]
    operations=[migrations.RunPython(backfill_authorship,migrations.RunPython.noop),migrations.RunSQL(SQL)]
