from apps.core.context import tenant_transaction
from apps.patient_portal.models import PatientLoginIdentity,PatientAccess


def open_access(world,client,patient,phone='13800000001'):
    return world.post(client,f'/api/patients/{patient.id}/portal-access/',{'phone':phone,'expected_revision':patient.revision})


def test_new_patient_login_uses_888888_and_requires_change(world):
    patient=world.patient('a');client=world.login('a','doctor')
    response=open_access(world,client,patient)
    assert response.status_code==200,response.content
    with tenant_transaction(patient.tenant_id):
        identity=PatientLoginIdentity.objects.get(phone='+8613800000001')
        assert identity.check_password('888888')
        assert identity.password!='888888'
        assert identity.must_change_password
    assert 'password' not in response.json()


def test_rebind_existing_phone_does_not_reset_password(world):
    first=world.patient('a');second=world.patient('a');client=world.login('a','doctor')
    assert open_access(world,client,first).status_code==200
    with tenant_transaction(first.tenant_id):
        identity=PatientLoginIdentity.objects.get(phone='+8613800000001')
        identity.set_password('Changed-Patient-Password!');identity.must_change_password=False;identity.save()
        previous=identity.password
    assert open_access(world,client,second).status_code==200
    with tenant_transaction(first.tenant_id):
        identity.refresh_from_db()
        assert identity.password==previous
        assert PatientAccess.objects.filter(identity=identity).count()==2


def test_contact_phone_does_not_grant_access(world):
    patient=world.patient('a',phone='13800000001')
    with tenant_transaction(patient.tenant_id):
        assert not PatientAccess.objects.filter(patient=patient).exists()


def test_other_doctor_cannot_open_access(world):
    patient=world.patient('a');other=world.doctor('a')
    from rest_framework.test import APIClient
    client=APIClient(enforce_csrf_checks=True)
    from apps.accounts.models import LoginIdentity
    phone=LoginIdentity.objects.using('migration').get(id=other.account.identity_id).phone
    response=world.post(client,'/api/auth/login/',{'phone':phone,'password':world.password})
    client.defaults['HTTP_X_WORKSPACE_TOKEN']=response.json()['workspace_token']
    assert open_access(world,client,patient).status_code==404


def test_access_failure_rolls_back_identity_patient_and_quota(world,monkeypatch):
    from apps.patients.services import create_patient
    def fail(*args,**kwargs):raise RuntimeError('模拟审计失败')
    monkeypatch.setattr('apps.patients.services.audit',fail)
    import pytest
    from apps.patients.models import Patient
    from apps.tenants.models import TenantQuota
    actor=world.actor('a','doctor')
    with pytest.raises(RuntimeError):
        create_patient(actor,{'code':'rollback-portal','name':'回滚患者','enable_patient_portal':True,'login_phone':'13800000009'})
    with tenant_transaction(actor.tenant_id):
        assert not Patient.objects.filter(code='rollback-portal').exists()
        assert not PatientLoginIdentity.objects.filter(phone='+8613800000009').exists()
        assert TenantQuota.objects.get(tenant_id=actor.tenant_id).patients_used==0


def test_concurrent_open_creates_one_identity(world):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import connections
    from apps.patient_portal.access import open_patient_access
    first=world.patient('a');second=world.patient('a');actor=world.actor('a','doctor');gate=Barrier(2)
    def run(patient):
        connections.close_all()
        try:
            gate.wait(timeout=10)
            return open_patient_access(actor,patient.id,'13800000003',patient.revision).identity_id
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,[first,second]))
    assert results[0]==results[1]
    with tenant_transaction(actor.tenant_id):
        assert PatientLoginIdentity.objects.filter(phone='+8613800000003').count()==1
        assert PatientAccess.objects.filter(identity_id=results[0]).count()==2
