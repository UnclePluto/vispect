from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from django.db import connections
from apps.accounts.models import LoginIdentity,Account
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from apps.doctors.services import create_doctor,delete_doctor
from apps.doctors.models import Doctor
from apps.tenants.models import TenantQuota

PHONE='13810000001'
def data(world,**kw):return {'login_phone':PHONE,'initial_password':world.password,'name':'手机医生',**kw}

def test_add_existing_phone_preserves_global_credentials(world):
    original=LoginIdentity.objects.using('control').get(id=world.accounts['a','tenant_admin'].identity_id)
    doctor=create_doctor(world.actor('b','tenant_admin'),data(world,login_phone=original.phone,initial_password='ignored'))
    original.refresh_from_db(using='control');assert doctor.account.identity_id==original.id
    assert original.check_password(world.password) and original.revision==1
    assert world.accounts['a','tenant_admin'].role=='tenant_admin'
    client=world.login('b','tenant_admin',unified=True)
    payload=client.get(f'/api/doctors/{doctor.id}/').json();assert payload['login_phone']==original.phone
    response=world.post(client,'/api/members/phone-status/',{'phone':original.phone})
    assert response.status_code==200 and response.json()=={'phone':original.phone,'registered':True}
    assert world.post(world.login('a','doctor',unified=True),'/api/members/phone-status/',{'phone':PHONE}).status_code==403

def test_duplicate_or_deleted_member_not_recreated(world):
    a=world.actor('a','tenant_admin');d=create_doctor(a,data(world))
    with pytest.raises(ApiError) as exc:create_doctor(a,data(world))
    assert exc.value.code=='member_exists'
    delete_doctor(a,d.id,d.revision)
    with pytest.raises(ApiError) as exc:create_doctor(a,data(world))
    assert exc.value.code=='member_deleted'
    with world.owner_context(a.tenant_id):assert Account.objects.using('migration').filter(identity_id=d.account.identity_id).count()==1

def test_concurrent_phone_provisioning(world,monkeypatch):
    from apps.doctors import services
    original=services.ensure_identity;barrier=Barrier(2)
    def ensure(*args,**kw):barrier.wait(10);return original(*args,**kw)
    monkeypatch.setattr(services,'ensure_identity',ensure)
    def create(slug):
        try:return create_doctor(world.actor(slug,'tenant_admin'),data(world,initial_password=f'Concurrent-{slug}-Strong-2026!'))
        finally:connections.close_all()
    with ThreadPoolExecutor(2) as pool:doctors=list(pool.map(create,['a','b']))
    assert doctors[0].account.identity_id==doctors[1].account.identity_id
    identity=LoginIdentity.objects.using('control').get(phone='+86'+PHONE)
    assert sum(identity.check_password(f'Concurrent-{s}-Strong-2026!') for s in ['a','b'])==1

@pytest.mark.parametrize('failure',['quota','doctor','audit'])
def test_member_failure_rolls_back_identity_and_doctor(world,monkeypatch,failure):
    from apps.doctors import services
    if failure=='quota':
        q=TenantQuota.objects.using('migration').get(tenant=world.tenants['a']);q.doctors_limit=1;world.owner_save(q)
    elif failure=='doctor':monkeypatch.setattr(Doctor.objects,'create',lambda **kw:(_ for _ in ()).throw(RuntimeError('doctor failed')))
    else:monkeypatch.setattr(services,'audit',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('audit failed')))
    with pytest.raises((RuntimeError,ApiError)):create_doctor(world.actor('a','tenant_admin'),data(world))
    assert not LoginIdentity.objects.using('control').filter(phone='+86'+PHONE).exists()
    with world.owner_context(world.tenants['a'].id):
        assert Doctor.objects.using('migration').count()==1
        assert Account.objects.using('migration').filter(tenant=world.tenants['a']).count()==2

@pytest.mark.parametrize('field,value',[('password','New-Strong-2026!'),('login_phone',PHONE),('identity_id','abc'),('role','tenant_admin')])
def test_member_patch_cannot_change_global_credentials(world,field,value):
    client=world.login('a','tenant_admin',unified=True);token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f"/api/doctors/{world.accounts['a','doctor'].doctor_id}/",{field:value,'expected_revision':1},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code==400
