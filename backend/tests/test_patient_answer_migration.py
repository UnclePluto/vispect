import uuid
import pytest
from django.db import connection, DatabaseError, transaction
from apps.core.context import tenant_transaction
from apps.followups.answers import submit_answer, revise_answer
from apps.followups.models import Answer, AnswerRevision


def test_original_submitter_and_before_after_history(world):
    actor=world.actor('a','doctor'); _,visit,binding=world.entry('a')
    answer=submit_answer(actor,visit.id,binding.id,{'q1':'患者原答案'},uuid.uuid4().hex)
    first_time=answer.submitted_at
    answer=revise_answer(world.actor('a','tenant_admin'),answer.id,{'q1':'医生修订'},'核对原记录',answer.revision)
    assert answer.submitted_by_id == actor.account_id
    assert answer.submitted_at == first_time
    assert answer.submission_source == 'proxy'
    with tenant_transaction(actor.tenant_id):
        history=AnswerRevision.objects.get(answer=answer)
        assert history.previous_answers == {'q1':'患者原答案'}
        assert history.new_answers == {'q1':'医生修订'}


def test_answer_recorder_exactly_one(world):
    actor=world.actor('a','doctor'); _,visit,binding=world.entry('a')
    answer=submit_answer(actor,visit.id,binding.id,{'q1':'答案'},uuid.uuid4().hex)
    with tenant_transaction(actor.tenant_id):
        with pytest.raises(DatabaseError),transaction.atomic():
            Answer.objects.filter(id=answer.id).update(recorded_by=None)


def test_history_is_immutable_after_migration(world):
    actor=world.actor('a','doctor'); _,visit,binding=world.entry('a')
    answer=submit_answer(actor,visit.id,binding.id,{'q1':'原答案'},uuid.uuid4().hex)
    revise_answer(actor,answer.id,{'q1':'新答案'},'校正',answer.revision)
    with tenant_transaction(actor.tenant_id):
        with pytest.raises(DatabaseError),transaction.atomic():
            AnswerRevision.objects.filter(answer=answer).update(reason='覆盖原因')


def test_migration_restores_first_submitter_from_oldest_revision(world):
    from django.apps import apps
    from django.db import connections
    from importlib import import_module
    actor=world.actor('a','doctor');_,visit,binding=world.entry('a')
    answer=submit_answer(actor,visit.id,binding.id,{'q1':'一'},uuid.uuid4().hex)
    answer=revise_answer(world.actor('a','tenant_admin'),answer.id,{'q1':'二'},'校对',answer.revision)
    answer=revise_answer(actor,answer.id,{'q1':'三'},'再校对',answer.revision)
    conn=connections['migration']
    with world.owner_context(actor.tenant_id):
        with conn.cursor() as cursor:
            cursor.execute('ALTER TABLE followups_answer DISABLE TRIGGER immutable_submission_origin')
            cursor.execute('ALTER TABLE followups_answerrevision DISABLE TRIGGER immutable_answer_history')
        Answer.objects.using('migration').filter(id=answer.id).update(submitted_by_id=world.actor('a','tenant_admin').account_id)
        AnswerRevision.objects.using('migration').filter(answer=answer).update(new_answers={})
        with conn.cursor() as cursor:cursor.execute('ALTER TABLE followups_answerrevision ENABLE TRIGGER immutable_answer_history')
        with conn.schema_editor() as editor:
            import_module('apps.followups.migrations.0006_patient_answer_security').backfill_authorship(apps,editor)
        with conn.cursor() as cursor:cursor.execute('ALTER TABLE followups_answer ENABLE TRIGGER immutable_submission_origin')
    with tenant_transaction(actor.tenant_id):
        answer.refresh_from_db()
        history=list(AnswerRevision.objects.filter(answer=answer).order_by('previous_revision'))
        assert answer.submitted_by_id==actor.account_id
        assert [h.new_answers for h in history]==[{'q1':'二'},{'q1':'三'}]
