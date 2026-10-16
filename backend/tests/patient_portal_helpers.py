from types import SimpleNamespace
from rest_framework.test import APIClient


def portal_world(world):
    from apps.patient_portal.access import open_patient_access
    from apps.patient_portal.entries import get_or_create_entry
    enrollment,visit,binding=world.entry('a');actor=world.actor('a','doctor')
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
