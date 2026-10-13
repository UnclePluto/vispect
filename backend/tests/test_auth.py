def test_csrf_endpoint_returns_token(client):
    response = client.get('/api/auth/csrf/')
    assert response.status_code == 200
    assert response.json()['csrf_token']
    assert 'csrftoken' in response.cookies

def test_login_requires_csrf(world):
    from rest_framework.test import APIClient
    client = APIClient(enforce_csrf_checks=True)
    response = client.post('/api/auth/tenant-login/', {'tenant':'a','username':'admin','password':world.password}, format='json')
    assert response.status_code == 403

def test_same_username_logs_into_separate_tenants(world):
    for slug in ['a','b']:
        client = world.login(slug, 'tenant_admin')
        identity = client.get('/api/auth/me/').json()
        assert identity['tenant_id'] == str(world.tenants[slug].id)
        assert identity['username'] == 'admin'

def test_deactivation_revokes_existing_session(world):
    client = world.login('a','tenant_admin')
    world.accounts['a','tenant_admin'].is_active = False
    world.owner_save(world.accounts['a','tenant_admin'])
    assert client.get('/api/auth/me/').status_code == 401

def test_disabled_tenant_revokes_existing_session(world):
    client = world.login('a','tenant_admin')
    world.tenants['a'].enabled = False
    world.owner_save(world.tenants['a'])
    assert client.get('/api/auth/me/').status_code == 401

def test_platform_cannot_enter_tenant_context(world):
    client = world.login(None,'platform_admin')
    response = client.get('/api/auth/me/')
    assert response.status_code == 200
    assert response.json()['tenant_id'] is None
    from apps.core.permissions import require_tenant
    import pytest
    from apps.core.errors import ApiError
    with pytest.raises(ApiError) as exc:
        require_tenant(world.actor(None,'platform_admin'))
    assert exc.value.status == 403

def test_password_change_is_required_and_invalidates_old_sessions(world):
    account = world.accounts['a','tenant_admin']
    account.must_change_password = True
    world.owner_save(account)
    client = world.login('a','tenant_admin')
    old_client = world.login('a','tenant_admin')
    assert client.get('/api/auth/me/').json()['must_change_password'] is True
    denied=world.post(client,'/api/patients/',{'name':'测试患者'})
    assert denied.status_code == 403
    assert denied.json()['code'] == 'password_change_required'
    response = world.post(client, '/api/auth/change-password/', {'old_password':world.password,'new_password':'New-Strong-Password-2026!'})
    assert response.status_code == 200
    assert client.get('/api/auth/me/').json()['must_change_password'] is False
    assert old_client.get('/api/auth/me/').status_code == 401

def test_client_cannot_switch_session_tenant(world):
    client = world.login('a','tenant_admin')
    response = client.get('/api/auth/me/', HTTP_X_TENANT_ID=str(world.tenants['b'].id))
    assert response.json()['tenant_id'] == str(world.tenants['a'].id)
