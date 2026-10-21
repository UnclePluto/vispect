from apps.core.context import tenant_transaction
from apps.patient_portal.access import open_patient_access
from apps.followups.enrollments import add_subject,confirm_enrollment
from apps.followups.answers import submit_answer
from apps.followups.transitions import complete_visit
from tests.patient_portal_helpers import portal_world,ready_patient,patient_post,login_patient
import uuid


def resolve(client,portal):return patient_post(client,'/api/patient/tasks/resolve/',{'entry_token':portal.entry.token})


def test_shared_qr_returns_only_explicitly_bound_enrolled_patients(world):
    portal=portal_world(world);client=ready_patient(portal)
    world.patient('a',phone='13800000001')
    response=resolve(client,portal)
    assert response.status_code==200,response.content
    assert [c['patient_id'] for c in response.json()['results']]==[str(portal.enrollment.patient_id)]


def test_same_name_choices_include_patient_code(world):
    portal=portal_world(world);other=world.patient('a')
    open_patient_access(portal.actor,other.id,'13800000001',other.revision)
    e=add_subject(portal.actor,portal.enrollment.study_id,other.id,portal.actor.doctor_id,'other',uuid.uuid4().hex)
    confirm_enrollment(portal.actor,e.id,'other',e.added_on,uuid.uuid4().hex)
    client=ready_patient(portal);choices=resolve(client,portal).json()['results']
    assert len(choices)==2
    assert len({c['patient_code'] for c in choices})==2


def test_patient_cannot_request_other_patient_or_doctor_form(world):
    portal=portal_world(world);client=ready_patient(portal);other=world.patient('a')
    response=client.get(f'/api/patient/entries/{portal.entry.token}/patients/{other.id}/')
    assert response.status_code==404
    assert 'definition' not in response.json()


def test_first_password_change_is_required_for_task_resolution(world):
    portal=portal_world(world);client,_=login_patient(portal)
    assert resolve(client,portal).status_code==403


def test_future_visit_is_read_only(world):
    portal=portal_world(world)
    from apps.patient_portal.entries import get_or_create_entry
    with tenant_transaction(portal.actor.tenant_id):binding=portal.enrollment.study.stages.get(kind='followup').bindings.first()
    portal.entry=get_or_create_entry(portal.actor,binding.id)
    client=ready_patient(portal)
    response=client.get(f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/')
    assert response.status_code==200,response.content
    assert response.json()['task_state']=='not_open'
    assert response.json()['writable'] is False


def test_completed_optional_unsubmitted_form_is_read_only(world):
    portal=portal_world(world,optional=True)
    complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
    client=ready_patient(portal)
    response=client.get(f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/')
    assert response.status_code==200,response.content
    assert response.json()['writable'] is False
    assert response.json()['task_state']=='visit_completed'
    assert response.json()['answer'] is None


def test_overdue_current_visit_remains_writable(world):
    portal=portal_world(world)
    from datetime import timedelta
    from django.utils import timezone
    portal.visit.window_end=timezone.localdate()-timedelta(days=5);world.owner_save(portal.visit)
    client=ready_patient(portal)
    response=client.get(f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/')
    assert response.json()['writable'] is True


def test_completed_followup_can_view_existing_answer_only(world):
    portal=portal_world(world)
    submit_answer(portal.actor,portal.visit.id,portal.binding.id,{'q1':'基线答案'},uuid.uuid4().hex)
    complete_visit(portal.actor,portal.visit.id,uuid.uuid4().hex)
    with tenant_transaction(portal.actor.tenant_id):
        portal.enrollment.refresh_from_db();last=portal.enrollment.current_visit
        binding=last.stage.bindings.first()
    submit_answer(portal.actor,last.id,binding.id,{'q1':'随访答案'},uuid.uuid4().hex)
    complete_visit(portal.actor,last.id,uuid.uuid4().hex)
    client=ready_patient(portal)
    response=client.get(f'/api/patient/entries/{portal.entry.token}/patients/{portal.enrollment.patient_id}/')
    assert response.status_code==200,response.content
    assert response.json()['writable'] is False
    assert response.json()['answer']['answers']=={'q1':'基线答案'}
