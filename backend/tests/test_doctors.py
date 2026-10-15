import pytest
import uuid
import psycopg
from concurrent.futures import ThreadPoolExecutor
from django.db import connections,DataError
from apps.core.errors import ApiError

def test_tenant_admin_can_create_doctor_with_chinese_name(world):
    client=world.login('a','tenant_admin')
    response=world.post(client,'/api/doctors/',{'login_phone':'13811000001','initial_password':world.password,'name':'  张  医生  ','phone':'13800000000','organization':'测试医院','department':'全科','title':'主治医师'})
    assert response.status_code == 201,response.content
    assert response.json()['name'] == '张  医生'
    assert 'password' not in response.json()

def test_last_doctor_slot_is_atomic(world):
    from apps.doctors.services import create_doctor
    from apps.tenants.models import TenantQuota
    world.doctor('a',username='existing')
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a'])
    assert quota.doctors_used == 2
    quota.doctors_limit=3;world.owner_save(quota)
    actor=world.actor('a','tenant_admin')
    def attempt(phone):
        try:
            create_doctor(actor,{'login_phone':phone,'initial_password':world.password,'name':phone})
            return True
        except ApiError as exc:
            assert exc.code=='quota_exceeded'
            return False
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,['13811000002','13811000003']))
    assert results.count(True) == 1
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).doctors_used == 3

def test_disable_delete_and_restore_use_correct_quota(world):
    from apps.doctors.services import set_doctor_enabled,delete_doctor,restore_doctor
    from apps.tenants.models import TenantQuota
    doctor=world.doctor('a',username='temporary')
    actor=world.actor('a','tenant_admin')
    doctor=set_doctor_enabled(actor,doctor.id,False,doctor.revision)
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).doctors_used == 2
    doctor=delete_doctor(actor,doctor.id,doctor.revision)
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).doctors_used == 1
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a']);quota.doctors_limit=1;world.owner_save(quota)
    with pytest.raises(ApiError) as exc:restore_doctor(actor,doctor.id,doctor.revision)
    assert exc.value.code == 'quota_exceeded'

def test_database_failure_does_not_leave_account_or_consume_quota(world):
    from apps.doctors.services import create_doctor
    from apps.accounts.models import Account
    from apps.tenants.models import TenantQuota
    with pytest.raises(DataError):
        create_doctor(world.actor('a','tenant_admin'),{'login_phone':'13811000004','initial_password':world.password,'name':'失败医生','organization':'x'*201})
    with world.owner_context(world.tenants['a'].id):
        assert not Account.objects.using('migration').filter(name='失败医生').exists()
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).doctors_used == 1

def test_direct_sql_cannot_exceed_quota(world):
    from apps.tenants.models import TenantQuota
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a']);quota.doctors_limit=1;world.owner_save(quota)
    with psycopg.connect(world.app_dsn) as conn:
        tenant=world.tenants['a'].id;account_id=uuid.uuid4()
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant)])
        conn.execute("INSERT INTO accounts_account(id,tenant_id,identity_id,username,name,password,role,is_active,must_change_password,revision,created_at) VALUES (%s,%s,%s,'sql-doctor','测试','unused','doctor',true,false,1,now())",[account_id,tenant,world.accounts['b','doctor'].identity_id])
        with pytest.raises(psycopg.errors.CheckViolation) as exc:
            conn.execute("INSERT INTO doctors_doctor(id,tenant_id,account_id,name,phone,organization,department,title,revision,created_at,updated_at) VALUES (%s,%s,%s,'测试','','','','',1,now(),now())",[uuid.uuid4(),tenant,account_id])
        assert exc.value.diag.constraint_name == 'quota_exceeded_doctors'

def test_doctor_cannot_change_role_or_other_doctor(world):
    doctor=world.doctor('a',username='other')
    client=world.login('a','doctor')
    me=world.accounts['a','doctor']
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f'/api/doctors/{me.doctor_id}/',{'role':'tenant_admin','expected_revision':1},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 400
    assert client.get(f'/api/doctors/{doctor.id}/').status_code == 404
    assert client.get('/api/doctors/').json()['count'] == 1

def test_platform_and_other_tenant_cannot_read_doctor(world):
    doctor=world.doctor('a',username='private')
    assert world.login(None,'platform_admin').get('/api/doctors/').status_code == 403
    assert world.login('b','tenant_admin').get(f'/api/doctors/{doctor.id}/').status_code == 404

def test_doctor_profile_and_account_use_same_tenant_constraint(world):
    from apps.accounts.models import Account
    foreign=Account(tenant=world.tenants['b'],username='unlinked',name='其他租户账号',role='doctor',password='unused')
    world.owner_save(foreign)
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute('UPDATE doctors_doctor SET account_id=%s WHERE id=%s',[foreign.id,world.accounts['a','doctor'].doctor_id])

def test_member_cannot_change_global_password(world):
    client=world.login('a','tenant_admin');doctor_id=world.accounts['a','doctor'].doctor_id
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f'/api/doctors/{doctor_id}/',{'name':'更新姓名','password':'','expected_revision':1},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 400
    assert world.login('a','doctor').get('/api/auth/me/').status_code == 200

def test_quota_adjustment_and_creation_do_not_deadlock(world):
    from threading import Event
    from apps.doctors.services import create_doctor
    from apps.tenants.services import update_tenant
    from apps.tenants.models import TenantQuota
    quota_held=Event();tenant_held=Event()
    def create():
        def coordinate(execute,statement,params,many,context):
            result=execute(statement,params,many,context)
            if 'FROM "tenants_tenantquota"' in statement and 'FOR UPDATE' in statement:
                quota_held.set();assert tenant_held.wait(10)
            return result
        try:
            with connections['default'].execute_wrapper(coordinate):
                return create_doctor(world.actor('a','tenant_admin'),{'login_phone':'13811000005','name':'并发医生','initial_password':world.password})
        finally:connections.close_all()
    def adjust():
        def coordinate(execute,statement,params,many,context):
            result=execute(statement,params,many,context)
            if 'FROM "tenants_tenant"' in statement and 'FOR ' in statement:
                tenant_held.set();assert quota_held.wait(10)
            return result
        try:
            with connections['control'].execute_wrapper(coordinate):
                return update_tenant(world.actor(None,'platform_admin'),world.tenants['a'].id,{'limits':{'doctors':200}},1)
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        one=pool.submit(create);two=pool.submit(adjust);one.result(timeout=15);two.result(timeout=15)
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a'])
    assert quota.doctors_used == 2
    assert quota.doctors_limit == 200
