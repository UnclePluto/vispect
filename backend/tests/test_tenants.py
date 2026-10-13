from django.db import DataError
import pytest

def test_platform_can_create_tenant_with_initial_admin(world):
    client=world.login(None,'platform_admin')
    response=world.post(client,'/api/platform/tenants/',{'slug':'new-clinic','name':'新测试机构','admin_username':'owner','admin_password':world.password,'limits':{'doctors':2,'patients':10,'studies':3}})
    assert response.status_code == 201,response.content
    assert response.json()['usage'] == {'doctors':0,'patients':0,'studies':0}
    from apps.tenants.models import Tenant,TenantQuota
    from apps.accounts.models import Account
    tenant=Tenant.objects.using('migration').get(slug='new-clinic')
    assert TenantQuota.objects.using('migration').get(tenant=tenant).doctors_limit == 2
    with world.owner_context(tenant.id):
        account=Account.objects.using('migration').get(tenant=tenant,username='owner')
        assert account.must_change_password
        assert account.check_password(world.password)

def test_tenant_admin_cannot_call_platform_api(world):
    client=world.login('a','tenant_admin')
    assert client.get('/api/platform/tenants/').status_code == 403

def test_tenant_creation_failure_is_atomic(world):
    from apps.tenants.services import create_tenant
    from apps.tenants.models import Tenant
    with pytest.raises(DataError):
        create_tenant(world.actor(None,'platform_admin'),{'slug':'failed','name':'不能残留','admin_username':'x'*151,'admin_password':world.password,'limits':{'doctors':2,'patients':10,'studies':3}})
    assert not Tenant.objects.using('migration').filter(slug='failed').exists()

def test_platform_usage_exposes_only_metadata_and_counts(world):
    client=world.login(None,'platform_admin')
    response=client.get('/api/platform/usage/')
    assert response.status_code == 200
    assert len(response.json()['results']) == 2
    for row in response.json()['results']:
        assert set(row) == {'tenant_id','tenant_name','doctors','patients','studies'}

def test_tenant_revision_conflict_keeps_existing_limits(world):
    client=world.login(None,'platform_admin')
    tenant=world.tenants['a']
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f'/api/platform/tenants/{tenant.id}/',{'name':'旧编辑','expected_revision':0},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 409
    assert response.json()['code'] == 'revision_conflict'

def test_empty_password_preserves_administrator_password(world):
    client=world.login(None,'platform_admin');tenant=world.tenants['a']
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f'/api/platform/tenants/{tenant.id}/administrator/',{'username':'admin','name':'更新管理员','enabled':True,'password':'','expected_revision':1},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert world.login('a','tenant_admin').get('/api/auth/me/').json()['name'] == '更新管理员'
