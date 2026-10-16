from types import SimpleNamespace
from rest_framework.test import APIClient


def portal_world(world,optional=False,definition=None):
    from apps.patient_portal.access import open_patient_access
    from apps.patient_portal.entries import get_or_create_entry
    actor=world.actor('a','doctor')
    if optional:
        import uuid
        from apps.core.context import tenant_transaction
        from apps.followups.enrollments import add_subject,confirm_enrollment
        study=world.study('a',definition=definition);patient=world.patient('a')
        with tenant_transaction(actor.tenant_id):binding=study.stages.get(kind='baseline').bindings.first()
        binding.required=False;world.owner_save(binding)
        enrollment=add_subject(actor,study.id,patient.id,actor.doctor_id,uuid.uuid4().hex,uuid.uuid4().hex)
        enrollment=confirm_enrollment(actor,enrollment.id,uuid.uuid4().hex,enrollment.added_on,uuid.uuid4().hex)
        with tenant_transaction(actor.tenant_id):visit=enrollment.current_visit;binding=visit.stage.bindings.select_related('form_version__form').first()
    else:enrollment,visit,binding=world.entry('a',definition=definition)
    access=open_patient_access(actor,enrollment.patient_id,'13800000001',1)
    entry=get_or_create_entry(actor,binding.id)
    return SimpleNamespace(enrollment=enrollment,visit=visit,binding=binding,access=access,entry=entry,actor=actor)


def patient_post(client,path,data,**extra):
    csrf=client.get('/api/patient/csrf/').json()['csrf_token']
    return client.post(path,data,format='json',HTTP_X_CSRFTOKEN=csrf,**extra)


def login_patient(portal,client=None):
    client=client or APIClient(enforce_csrf_checks=True)
    response=patient_post(client,'/api/patient/auth/login/',{'entry_token':portal.entry.token,'phone':'13800000001','password':'888888'})
    assert response.status_code==200,response.content
    client.defaults['HTTP_X_PATIENT_SESSION_TOKEN']=response.json()['session_token']
    return client,response


def ready_patient(portal,client=None):
    client,_=login_patient(portal,client)
    response=patient_post(client,'/api/patient/auth/change-password/',{'old_password':'888888','new_password':'Patient-Changed-Password-2026!'})
    assert response.status_code==200,response.content
    client.defaults['HTTP_X_PATIENT_SESSION_TOKEN']=response.json()['session_token']
    return client
