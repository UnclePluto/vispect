import pytest
from rest_framework.test import APIClient,APIRequestFactory
from apps.core.errors import ApiError
from tests.patient_portal_helpers import portal_world,patient_post,login_patient,ready_patient


def test_first_login_blocks_all_clinical_endpoints(world):
    portal=portal_world(world);client,response=login_patient(portal)
    assert response.json()['next']=='change_password'
    from apps.patient_portal.sessions import patient_transaction
    from django.conf import settings
    factory=APIRequestFactory();request=factory.get('/api/patient/tasks/resolve/',HTTP_X_PATIENT_SESSION_TOKEN=response.json()['session_token'])
    name=settings.PATIENT_SESSION_COOKIE_NAME
    request.COOKIES[name]=client.cookies[name].value
    with pytest.raises(ApiError) as exc:
        with patient_transaction(request):pass
    assert exc.value.status==403
    assert response.cookies[name]['httponly']
    assert response.cookies[name]['path']=='/api/patient/'


def test_patient_password_does_not_change_staff_identity(world):
    portal=portal_world(world);client=world.login('a','doctor')
    from apps.accounts.models import LoginIdentity
    staff=LoginIdentity.objects.using('migration').get(id=world.accounts['a','doctor'].identity_id);original=staff.password
    client=ready_patient(portal,client)
    staff.refresh_from_db(using='migration')
    assert staff.password==original
    assert client.get('/api/auth/me/').status_code==200
    assert client.get('/api/patient/auth/me/').json()['next']=='ready'
    assert patient_post(client,'/api/patient/auth/logout/',{}).status_code==200
    assert client.get('/api/patient/auth/me/').status_code==401
    assert client.get('/api/auth/me/').status_code==200


def test_patient_login_requires_csrf(world):
    portal=portal_world(world);client=APIClient(enforce_csrf_checks=True)
    response=client.post('/api/patient/auth/login/',{'entry_token':portal.entry.token,'phone':'13800000001','password':'888888'},format='json')
    assert response.status_code==403


def test_patient_password_change_revokes_other_sessions(world):
    portal=portal_world(world);first,_=login_patient(portal);second,_=login_patient(portal)
    response=patient_post(first,'/api/patient/auth/change-password/',{'old_password':'888888','new_password':'Patient-Changed-Password-2026!'})
    assert response.status_code==200,response.content
    assert second.get('/api/patient/auth/me/').status_code==401
    assert first.get('/api/patient/auth/me/').json()['next']=='ready'


def test_invalid_credentials_do_not_reveal_patient(world):
    portal=portal_world(world);client=APIClient(enforce_csrf_checks=True)
    for phone,password in [('13800000001','wrong'),('13800009999','wrong')]:
        response=patient_post(client,'/api/patient/auth/login/',{'entry_token':portal.entry.token,'phone':phone,'password':password})
        assert response.status_code==401
        assert response.json()['message']=='手机号或密码不正确'
        assert 'patient' not in response.json()
