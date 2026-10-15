from concurrent.futures import ThreadPoolExecutor
from threading import Event,Barrier
from datetime import timedelta
import time
import pytest
from django.db import connections,transaction
from django.test import RequestFactory
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.test import APIClient
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from apps.accounts.models import LoginSessionContext

def multi(world):
    world.bind_identity(world.accounts['a','tenant_admin'],'13800000001')
    world.bind_identity(world.accounts['b','doctor'],'13800000001')
    client=APIClient(enforce_csrf_checks=True)
    response=world.post(client,'/api/auth/login/',{'phone':'13800000001','password':world.password})
    assert response.status_code==200
    return client,response.json()

def switch(world,client,account,token):
    return world.post(client,'/api/auth/switch-workspace/',{'account_id':str(account.id),'workspace_token':token})

def selected(world):
    client,envelope=multi(world);response=switch(world,client,world.accounts['a','tenant_admin'],envelope['workspace_token'])
    assert response.status_code==200
    return client,response.json()

def raw(client,token):
    from apps.accounts.principal import load_principal
    from django.conf import settings
    request=RequestFactory().get('/api/patients/',HTTP_X_WORKSPACE_TOKEN=token)
    request.session=SessionStore(session_key=client.cookies[settings.SESSION_COOKIE_NAME].value)
    load_principal(request)
    return request

def test_switch_requires_owned_active_workspace(world):
    client,data=multi(world)
    response=switch(world,client,world.accounts['b','doctor'],data['workspace_token']);assert response.status_code==200
    changed=response.json();assert changed['actor']['role']=='doctor' and changed['actor']['tenant_id']==str(world.tenants['b'].id)
    assert changed['workspace_token']!=data['workspace_token']
    assert switch(world,client,world.accounts['b','tenant_admin'],changed['workspace_token']).status_code==404
    assert client.get('/api/platform/tenants/',HTTP_X_WORKSPACE_TOKEN=changed['workspace_token']).status_code==403

def test_stale_workspace_token_rejected(world):
    client,data=selected(world);old=data['workspace_token']
    changed=switch(world,client,world.accounts['b','doctor'],old).json();token=changed['workspace_token']
    for headers in [{},{'HTTP_X_WORKSPACE_TOKEN':old}]:
        response=client.get('/api/patients/',**headers)
        assert response.status_code==409 and response.json()['code']=='workspace_changed'
    assert client.get('/api/patients/',HTTP_X_WORKSPACE_TOKEN=token,HTTP_X_TENANT_ID=str(world.tenants['a'].id)).status_code==200
    assert client.get('/api/auth/me/').json()['actor']['tenant_id']==str(world.tenants['b'].id)

@pytest.mark.parametrize('disabled',['member','organization'])
def test_member_revocation_keeps_other_workspace(world,disabled):
    client,data=selected(world)
    if disabled=='member':
        account=world.accounts['a','tenant_admin'];account.is_active=False;world.owner_save(account)
    else:
        organization=world.tenants['a'];organization.enabled=False;world.owner_save(organization)
    response=client.get('/api/patients/',HTTP_X_WORKSPACE_TOKEN=data['workspace_token'])
    assert response.status_code==409 and response.json()['code']=='workspace_unavailable'
    envelope=client.get('/api/auth/me/').json();assert envelope['user'] and envelope['actor'] is None
    assert switch(world,client,world.accounts['b','doctor'],envelope['workspace_token']).status_code==200

def waiting_lock(context_id,mode):
    from apps.core.workspace_lock import workspace_lock_key
    key=workspace_lock_key(context_id)&((1<<64)-1)
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        with connections['migration'].cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND classid=%s::oid AND objid=%s::oid AND mode=%s AND NOT granted)",[key>>32,key&0xffffffff,mode])
            if cursor.fetchone()[0]:return
        time.sleep(0.01)
    pytest.fail('未观察到预期数据库等待锁')

def test_switch_waits_for_authorized_write(world):
    from apps.accounts.workspaces import workspace_transaction,switch_workspace
    from apps.patients.services import create_patient
    client,data=selected(world);context_id=LoginSessionContext.objects.using('control').get().id
    entered=Event();release=Event()
    def writer():
        try:
            request=raw(client,data['workspace_token'])
            with workspace_transaction(request,using='default') as actor:
                entered.set();assert release.wait(10)
                return create_patient(actor,{'name':'旧机构已获准写入','code':'before-switch','doctor_ids':[world.accounts['a','doctor'].doctor_id]}).id
        finally:connections.close_all()
    def changer():
        try:return switch_workspace(raw(client,data['workspace_token']),world.accounts['b','doctor'].id,data['workspace_token'])
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        written=pool.submit(writer);assert entered.wait(8);changed=pool.submit(changer)
        try:waiting_lock(context_id,'ExclusiveLock');assert not changed.done()
        finally:release.set()
        patient_id=written.result(timeout=10);assert changed.result(timeout=10)['actor']['role']=='doctor'
    from apps.patients.models import Patient
    with tenant_transaction(world.tenants['a'].id):assert Patient.objects.filter(id=patient_id).exists()
    with tenant_transaction(world.tenants['b'].id):assert not Patient.objects.filter(code='before-switch').exists()

def test_waiting_old_write_revalidates_token(world):
    from apps.accounts.workspaces import workspace_transaction,switch_workspace
    from apps.core.workspace_lock import lock_workspace_context
    from apps.patients.services import create_patient
    client,data=selected(world);context_id=LoginSessionContext.objects.using('control').get().id
    entered=Event()
    def writer():
        try:
            request=raw(client,data['workspace_token']);entered.set()
            with workspace_transaction(request,using='default') as actor:
                create_patient(actor,{'name':'不能误写','code':'stale-write','doctor_ids':[world.accounts['a','doctor'].doctor_id]})
            return 'unexpected_success'
        except ApiError as exc:return exc.code
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic(using='control'):
            lock_workspace_context(context_id,using='control',exclusive=True)
            result=pool.submit(writer);assert entered.wait(8);waiting_lock(context_id,'ShareLock')
            switch_workspace(raw(client,data['workspace_token']),world.accounts['b','doctor'].id,data['workspace_token'])
        assert result.result(timeout=10)=='workspace_changed'

def test_concurrent_switch_only_one_wins(world):
    from apps.accounts.workspaces import switch_workspace
    client,data=selected(world);barrier=Barrier(2)
    def run(_):
        try:
            request=raw(client,data['workspace_token']);barrier.wait(timeout=8)
            switch_workspace(request,world.accounts['b','doctor'].id,data['workspace_token']);return 'ok'
        except ApiError as exc:return exc.code
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(run,[1,2]))==['ok','workspace_changed']

def test_revoked_old_snapshot_cannot_clear_new_workspace(world):
    from apps.accounts.workspaces import switch_workspace
    from apps.accounts.session_context import current_workspace
    client,data=selected(world);old_request=raw(client,data['workspace_token'])
    account=world.accounts['a','tenant_admin'];account.is_active=False;world.owner_save(account)
    changed=switch_workspace(raw(client,data['workspace_token']),world.accounts['b','doctor'].id,data['workspace_token'])
    workspace=current_workspace(old_request)
    assert workspace is not None and workspace['account_id']==str(world.accounts['b','doctor'].id)
    context=LoginSessionContext.objects.using('control').get()
    assert str(context.workspace_token)==changed['workspace_token']

def test_unified_platform_has_no_implicit_organization_membership(world):
    client=world.login(None,'platform_admin')
    data=client.get('/api/auth/me/').json()
    assert client.get('/api/platform/tenants/').status_code==200
    assert client.get('/api/patients/').status_code==403
    assert switch(world,client,world.accounts['a','tenant_admin'],data['workspace_token']).status_code==404
