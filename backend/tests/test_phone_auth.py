import pytest
from rest_framework.test import APIClient
from apps.accounts.models import LoginIdentity,LoginSessionContext
from django.utils import timezone
from datetime import timedelta

def bind(world,kind='single',must_change=False):
    account=world.accounts['a','tenant_admin'];identity=world.bind_identity(account,'13800000001')
    if kind=='multi':world.bind_identity(world.accounts['b','doctor'],'13800000001')
    elif kind=='none':account.is_active=False;world.owner_save(account)
    identity.must_change_password=must_change;identity.save(using='control')
    return identity

def login(world,phone='13800000001',password=None):
    client=APIClient(enforce_csrf_checks=True)
    response=world.post(client,'/api/auth/login/',{'phone':phone,'password':password or world.password})
    return client,response

@pytest.mark.parametrize('kind,expected',[('single','ready'),('multi','choose_workspace'),('none','no_workspace')])
def test_login_next_state(world,kind,expected):
    bind(world,kind);client,response=login(world)
    assert response.status_code==200
    data=response.json();assert data['next']==expected
    assert data['user']['phone']=='+8613800000001'
    assert (data['actor'] is not None)==(expected=='ready')
    assert client.get('/api/auth/me/').json()['user']['id']==data['user']['id']

def test_phone_login_requires_csrf(world):
    bind(world);client=APIClient(enforce_csrf_checks=True)
    assert client.post('/api/auth/login/',{'phone':'13800000001','password':world.password},format='json').status_code==403

@pytest.mark.parametrize('phone,password',[('13800000009','bad'),('13800000001','bad')])
def test_invalid_credentials_do_not_reveal_memberships(world,phone,password):
    bind(world);_,response=login(world,phone,password)
    assert response.status_code==401
    assert response.json()['message']=='手机号或密码不正确'
    assert 'workspaces' not in response.json()

def test_workspace_roles_do_not_union(world):
    bind(world,'multi');client,response=login(world);data=response.json()
    assert data['actor'] is None
    assert {w['role'] for w in data['workspaces']}=={'tenant_admin','doctor'}
    assert client.get('/api/patients/').status_code==403

def test_identity_password_revokes_other_sessions(world):
    bind(world,'multi',must_change=True);client,response=login(world);other,_=login(world)
    assert response.json()['next']=='change_password' and response.json()['actor'] is None
    changed=world.post(client,'/api/auth/change-password/',{'old_password':world.password,'new_password':'Unified-New-Strong-Password!2026'})
    assert changed.status_code==200 and not changed.json()['user']['must_change_password']
    assert client.get('/api/auth/me/').status_code==200
    assert other.get('/api/auth/me/').status_code==401
    identity=LoginIdentity.objects.using('control').get(phone='+8613800000001');assert identity.check_password('Unified-New-Strong-Password!2026')

def test_global_deactivation(world):
    identity=bind(world);client,response=login(world);assert response.status_code==200
    identity.is_active=False;identity.save(using='control')
    assert client.get('/api/auth/me/').status_code==401

def test_expired_context_rejected(world):
    bind(world);client,response=login(world);assert response.status_code==200
    LoginSessionContext.objects.using('control').update(expires_at=timezone.now()-timedelta(seconds=1))
    assert client.get('/api/auth/me/').status_code==401

def test_identity_initial_password_cannot_be_reused(world):
    bind(world,must_change=True);client,response=login(world);assert response.status_code==200
    denied=world.post(client,'/api/patients/',{'name':'不应创建'})
    assert denied.status_code==403 and denied.json()['code']=='password_change_required'
    response=world.post(client,'/api/auth/change-password/',{'old_password':world.password,'new_password':world.password})
    assert response.status_code==400
    assert client.get('/api/auth/me/').json()['next']=='change_password'

def test_phone_login_rejects_scope_injection_fields(world):
    bind(world);client=APIClient(enforce_csrf_checks=True)
    response=world.post(client,'/api/auth/login/',{'phone':'13800000001','password':world.password,'role':'platform_admin','tenant_id':str(world.tenants['b'].id)})
    assert response.status_code==400
