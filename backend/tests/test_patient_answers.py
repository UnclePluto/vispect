import uuid
from apps.core.context import tenant_transaction
from apps.patient_portal.models import PatientSubmissionReceipt
from apps.followups.models import Answer
from apps.followups.transitions import complete_visit
from apps.followups.answers import save_answer_draft
from tests.patient_portal_helpers import portal_world,ready_patient,patient_post


def write(client,portal,answers,action='submit',revision=0,key=None):
    extra={'HTTP_IDEMPOTENCY_KEY':key or uuid.uuid4().hex} if action=='submit' else {}
    return patient_post(client,f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/answers/',{'action':action,'answers':answers,'expected_revision':revision},**extra)


def test_patient_submit_records_real_origin(world):
    portal=portal_world(world);client=ready_patient(portal)
    response=write(client,portal,{'q1':'患者答案'})
    assert response.status_code==200,response.content
    with tenant_transaction(portal.actor.tenant_id):
        answer=Answer.objects.get(visit_id=portal.visit.id)
        assert answer.submission_source=='patient'
        assert answer.recorded_by_id is None
        assert answer.submitted_by_patient_id==portal.access.identity_id
        assert answer.is_proxy is False
        assert answer.answers=={'q1':'患者答案'}
        assert portal.enrollment.visits.get(id=portal.visit.id).status=='pending'


def test_retry_after_completed_visit_returns_existing_receipt(world):
    portal=portal_world(world);client=ready_patient(portal);key=uuid.uuid4().hex
    first=write(client,portal,{'q1':'答案'},key=key)
    assert first.status_code==200,first.content
    complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
    retry=write(client,portal,{'q1':'答案'},key=key)
    assert retry.status_code==200,retry.content
    assert retry.json()['id']==first.json()['id']
    assert retry.json()['submitted_at']==first.json()['submitted_at']
    assert write(client,portal,{'q1':'不同答案'},key=key).status_code==409
    with tenant_transaction(portal.actor.tenant_id):assert PatientSubmissionReceipt.objects.count()==1


def test_revoked_entry_cannot_read_submission_receipt(world):
    from apps.patient_portal.entries import change_entry
    portal=portal_world(world);client=ready_patient(portal);key=uuid.uuid4().hex
    assert write(client,portal,{'q1':'答案'},key=key).status_code==200
    change_entry(portal.actor,portal.entry.id,'disable',portal.entry.revision)
    response=write(client,portal,{'q1':'答案'},key=key)
    assert response.status_code==404
    assert 'answers' not in response.json()


def test_proxy_and_patient_share_revision_checked_draft(world):
    portal=portal_world(world);client=ready_patient(portal)
    response=write(client,portal,{'q1':'患者草稿'},'draft')
    assert response.status_code==200,response.content
    revision=response.json()['revision']
    staff=save_answer_draft(portal.actor,portal.visit.id,portal.binding.id,{'q1':'医生更新'},revision)
    assert write(client,portal,{'q1':'患者旧稿'},revision=revision).status_code==409
    response=write(client,portal,{'q1':'患者核对后提交'},revision=staff.revision)
    assert response.status_code==200,response.content
    assert response.json()['submission_source']=='patient'


def test_patient_cannot_submit_doctor_binding_or_extra_fields(world):
    portal=portal_world(world);client=ready_patient(portal)
    response=patient_post(client,f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/answers/',{'action':'submit','answers':{'q1':'答案'},'expected_revision':0,'binding_id':str(portal.binding.id)},HTTP_IDEMPOTENCY_KEY=uuid.uuid4().hex)
    assert response.status_code==400


def test_hidden_answers_are_cleaned_by_shared_engine(world):
    definition={'protocol_version':1,'title':'条件表单','questions':[{'id':'q1','type':'radio','title':'是否有症状','required':True,'options':[{'id':'no','label':'没有'},{'id':'yes','label':'有'}]},{'id':'q2','type':'text','title':'症状详情','required':True,'condition':{'mode':'all','rules':[{'question_id':'q1','operator':'eq','value':'yes'}]}}]}
    portal=portal_world(world,definition=definition);client=ready_patient(portal)
    response=write(client,portal,{'q1':'no','q2':'隐藏答案'})
    assert response.status_code==200,response.content
    assert response.json()['answers']=={'q1':'no'}
