import pytest
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError

def test_doctor_sees_only_assigned_patients(world):
    from apps.patients.services import create_patient
    from apps.patients.selectors import visible_patients
    a=world.actor('a','doctor')
    one=create_patient(a,{'code':'000001','name':'甲','phone':'13800000000'})
    other=world.doctor('a');two=world.patient('a',code='000002',doctor_ids=[other.id],phone='13800000000')
    with tenant_transaction(a.tenant_id):assert set(visible_patients(a))=={one}
    client=world.login('a','doctor')
    assert client.get('/api/patients/').json()['count']==1
    assert client.get(f'/api/patients/{two.id}/').status_code==404
    assert client.get(f'/api/patients/{one.id}/').json()['code']=='000001'
    assert world.login('a','tenant_admin').get('/api/patients/').json()['count']==2

def test_responsibility_change_revokes_access(world):
    from apps.patients.services import assign_doctors
    patient=world.patient('a');client=world.login('a','doctor');other=world.doctor('a')
    assert client.get(f'/api/patients/{patient.id}/').status_code==200
    assign_doctors(world.actor('a','tenant_admin'),patient.id,[other.id],patient.revision)
    assert client.get(f'/api/patients/{patient.id}/').status_code==404
    assert client.get('/api/patients/?search=测试').json()['count']==0

def test_cross_tenant_and_empty_assignment_rejected(world):
    from apps.patients.services import assign_doctors
    p=world.patient('a');admin=world.actor('a','tenant_admin')
    for ids in [[],[world.accounts['b','doctor'].doctor_id]]:
        with pytest.raises(ApiError):assign_doctors(admin,p.id,ids,p.revision)
    with pytest.raises(ApiError):assign_doctors(world.actor('a','doctor'),p.id,[world.accounts['a','doctor'].doctor_id],p.revision)
    assert world.login('b','tenant_admin').get(f'/api/patients/{p.id}/').status_code==404
    assert world.login(None,'platform_admin').get('/api/patients/').status_code==403

def test_patient_restore_checks_quota_and_doctor_delete_requires_transfer(world):
    from apps.patients.services import delete_patient,restore_patient
    from apps.doctors.services import delete_doctor
    from apps.tenants.models import TenantQuota
    p=world.patient('a');actor=world.actor('a','tenant_admin');doctor=world.accounts['a','doctor']
    with pytest.raises(ApiError) as exc:delete_doctor(actor,doctor.doctor_id,1)
    assert exc.value.code=='doctor_has_patients'
    p=delete_patient(actor,p.id,p.revision)
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a']);quota.patients_limit=0;world.owner_save(quota)
    with pytest.raises(ApiError) as exc:restore_patient(actor,p.id,p.revision)
    assert exc.value.code=='quota_exceeded'

def test_patient_validation_and_revision(world):
    client=world.login('a','doctor')
    for data in [{'code':123,'name':'测试'},{'code':'a','name':'测试','birth_date':'2999-01-01'},{'code':'a','name':'测试','doctor_ids':[]}]:
        assert world.post(client,'/api/patients/',data).status_code==400
    p=world.patient('a');token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f'/api/patients/{p.id}/',{'name':'修改','expected_revision':0},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code==409

def test_patient_rls_and_responsibility_foreign_key(world):
    import psycopg
    p=world.patient('a');world.patient('b')
    with psycopg.connect(world.app_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM patients_patient').fetchone()[0]==0
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
        assert conn.execute('SELECT id FROM patients_patient').fetchall()==[(p.id,)]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute('UPDATE patients_patientdoctor SET doctor_id=%s WHERE patient_id=%s',[world.accounts['b','doctor'].doctor_id,p.id])

def test_patient_restore_retains_identity_and_responsibility(world):
    from apps.patients.services import delete_patient,restore_patient
    from apps.tenants.models import TenantQuota
    p=world.patient('a',code='000001');actor=world.actor('a','tenant_admin')
    p=delete_patient(actor,p.id,p.revision);p=restore_patient(actor,p.id,p.revision)
    detail=world.login('a','doctor').get(f'/api/patients/{p.id}/').json()
    assert detail['code']=='000001' and len(detail['doctors'])==1
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).patients_used==1
