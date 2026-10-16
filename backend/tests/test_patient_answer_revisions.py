import uuid
import pytest
from io import BytesIO
from openpyxl import load_workbook
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from apps.followups.models import Answer,AnswerRevision
from apps.followups.answers import revise_answer,submit_answer
from apps.followups.transitions import complete_visit,stop_followup
from tests.patient_portal_helpers import portal_world,ready_patient
from tests.test_patient_answers import write


def submitted_patient(world):
    portal=portal_world(world);client=ready_patient(portal)
    response=write(client,portal,{'q1':'患者原答案'})
    assert response.status_code==200,response.content
    with tenant_transaction(portal.actor.tenant_id):answer=Answer.objects.get(id=response.json()['id'])
    return portal,answer


def test_revise_completed_patient_answer_preserves_origin_and_progress(world):
    portal,answer=submitted_patient(world);when=answer.submitted_at
    complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
    with tenant_transaction(portal.actor.tenant_id):portal.enrollment.refresh_from_db();current=portal.enrollment.current_visit_id
    updated=revise_answer(portal.actor,answer.id,{'q1':'医生核对答案'},'按原始记录核对',answer.revision)
    assert updated.submitted_by_patient_id==portal.access.identity_id
    assert updated.submitted_at==when
    assert updated.submission_source=='patient'
    assert updated.recorded_by_id==portal.actor.account_id
    with tenant_transaction(portal.actor.tenant_id):
        portal.enrollment.refresh_from_db()
        assert portal.enrollment.current_visit_id==current
        history=AnswerRevision.objects.get(answer=answer)
        assert history.previous_recorded_by_patient_id==portal.access.identity_id
        assert history.previous_answers=={'q1':'患者原答案'}
        assert history.new_answers=={'q1':'医生核对答案'}
    response=world.login('a','doctor').get(f'/api/answers/{answer.id}/revisions/')
    assert response.status_code==200,response.content
    row=response.json()['results'][0]
    assert row['definition']['questions'][0]['title']=='测试题目'
    assert row['new_answers']=={'q1':'医生核对答案'}


def test_patient_origin_export_has_no_null_staff_crash(world):
    from apps.followups.exports import export_answers
    portal,answer=submitted_patient(world)
    book=load_workbook(BytesIO(export_answers(portal.actor,answer_id=answer.id)))
    rows=list(book.active.values)
    assert rows[1][6]=='患者原答案'
    assert '患者自填' in rows[1]
    assert '原始提交人' in rows[0]


@pytest.mark.parametrize('mode',['stop','study_pause','form_pause','ended','unowned'])
def test_revise_stopped_paused_ended_or_unowned_patient_denied(world,mode):
    portal,answer=submitted_patient(world)
    if mode=='stop':stop_followup(portal.actor,portal.enrollment.id,'withdrawal','退出',uuid.uuid4().hex)
    elif mode=='study_pause':
        from apps.studies.services import set_study_state
        with tenant_transaction(portal.actor.tenant_id):study=portal.enrollment.study;study.refresh_from_db()
        set_study_state(portal.actor,study.id,'paused',study.revision)
    elif mode=='form_pause':
        from apps.forms.services import set_form_paused
        with tenant_transaction(portal.actor.tenant_id):form=portal.binding.form_version.form
        set_form_paused(world.actor('a','tenant_admin'),form.id,True,form.revision)
    elif mode=='ended':
        from apps.studies.services import set_study_state
        complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
        with tenant_transaction(portal.actor.tenant_id):
            portal.enrollment.refresh_from_db();last=portal.enrollment.current_visit;binding=last.stage.bindings.first()
        submit_answer(portal.actor,last.id,binding.id,{'q1':'结束答案'},uuid.uuid4().hex)
        complete_visit(portal.actor,last.id,uuid.uuid4().hex)
        with tenant_transaction(portal.actor.tenant_id):study=portal.enrollment.study;study.refresh_from_db()
        set_study_state(portal.actor,study.id,'ended',study.revision)
    else:
        from apps.core.types import Actor
        other=world.doctor('a');portal.actor=Actor(other.account_id,other.tenant_id,'doctor',other.id)
    with pytest.raises(ApiError):revise_answer(portal.actor,answer.id,{'q1':'不允许'},'原因',answer.revision)


def test_completed_optional_unsubmitted_answer_cannot_be_created_by_revision(world):
    portal=portal_world(world,optional=True)
    complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
    client=world.login('a','doctor')
    response=client.get(f'/api/visits/{portal.visit.id}/answers/')
    assert response.json()['results']==[]
    from apps.followups.answers import save_answer_draft
    with pytest.raises(ApiError):save_answer_draft(portal.actor,portal.visit.id,portal.binding.id,{'q1':'补填'},0)


def test_completed_doctor_answer_remains_locked(world):
    _,visit,binding=world.entry('a',respondent='doctor');actor=world.actor('a','doctor')
    answer=submit_answer(actor,visit.id,binding.id,{'q1':'医生原答案'},uuid.uuid4().hex)
    complete_visit(actor,visit.id,uuid.uuid4().hex)
    with pytest.raises(ApiError):revise_answer(actor,answer.id,{'q1':'修改'},'原因',answer.revision)


def test_multiple_revisions_preserve_first_patient_submission(world):
    portal,answer=submitted_patient(world);first_time=answer.submitted_at
    for text in ['一次修订','二次修订']:
        answer=revise_answer(portal.actor,answer.id,{'q1':text},'核对',answer.revision)
    assert answer.submitted_by_patient_id==portal.access.identity_id
    assert answer.submitted_at==first_time
    with tenant_transaction(portal.actor.tenant_id):
        history=list(AnswerRevision.objects.filter(answer=answer).order_by('previous_revision'))
        assert len(history)==2
        assert history[0].previous_answers=={'q1':'患者原答案'}
        assert history[1].new_answers=={'q1':'二次修订'}
