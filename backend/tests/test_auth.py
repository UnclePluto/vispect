def test_csrf_endpoint_returns_token(client):
    response = client.get('/api/auth/csrf/')
    assert response.status_code == 200
    assert response.json()['csrf_token']
    assert 'csrftoken' in response.cookies

def test_login_requires_csrf(world):
    from rest_framework.test import APIClient
    client = APIClient(enforce_csrf_checks=True)
    response = client.post('/api/auth/login/', {'phone':world.phone_for('a','tenant_admin'),'password':world.password}, format='json')
    assert response.status_code == 403

def test_phone_identity_enters_its_organization(world):
    for slug in ['a','b']:
        client = world.login(slug, 'tenant_admin')
        identity = client.get('/api/auth/me/').json()
        assert identity['actor']['tenant_id'] == str(world.tenants[slug].id)
        assert identity['user']['phone']=='+86'+world.phone_for(slug,'tenant_admin')

def test_deactivation_revokes_existing_session(world):
    client = world.login('a','tenant_admin')
    world.accounts['a','tenant_admin'].is_active = False
    world.owner_save(world.accounts['a','tenant_admin'])
    data=client.get('/api/auth/me/').json();assert data['user'] and data['actor'] is None

def test_disabled_tenant_revokes_existing_session(world):
    client = world.login('a','tenant_admin')
    world.tenants['a'].enabled = False
    world.owner_save(world.tenants['a'])
    data=client.get('/api/auth/me/').json();assert data['user'] and data['actor'] is None

def test_platform_cannot_enter_tenant_context(world):
    client = world.login(None,'platform_admin')
    response = client.get('/api/auth/me/')
    assert response.status_code == 200
    assert response.json()['actor']['tenant_id'] is None
    from apps.core.permissions import require_tenant
    import pytest
    from apps.core.errors import ApiError
    with pytest.raises(ApiError) as exc:
        require_tenant(world.actor(None,'platform_admin'))
    assert exc.value.status == 403

def test_password_change_is_required_and_invalidates_old_sessions(world):
    account = world.accounts['a','tenant_admin']
    from apps.accounts.models import LoginIdentity
    LoginIdentity.objects.using('control').filter(id=account.identity_id).update(must_change_password=True)
    client = world.login('a','tenant_admin')
    old_client = world.login('a','tenant_admin')
    assert client.get('/api/auth/me/').json()['user']['must_change_password'] is True
    denied=world.post(client,'/api/patients/',{'name':'测试患者'})
    assert denied.status_code == 403
    assert denied.json()['code'] == 'password_change_required'
    response = world.post(client, '/api/auth/change-password/', {'old_password':world.password,'new_password':'New-Strong-Password-2026!'})
    assert response.status_code == 200
    assert client.get('/api/auth/me/').json()['user']['must_change_password'] is False
    assert old_client.get('/api/auth/me/').status_code == 401

def test_client_cannot_switch_session_tenant(world):
    client = world.login('a','tenant_admin')
    response = client.get('/api/auth/me/', HTTP_X_TENANT_ID=str(world.tenants['b'].id))
    assert response.json()['actor']['tenant_id'] == str(world.tenants['a'].id)

def test_initial_password_cannot_be_reused(world):
    account=world.accounts['a','tenant_admin']
    from apps.accounts.models import LoginIdentity
    LoginIdentity.objects.using('control').filter(id=account.identity_id).update(must_change_password=True)
    client=world.login('a','tenant_admin')
    response=world.post(client,'/api/auth/change-password/',{'old_password':world.password,'new_password':world.password})
    assert response.status_code == 400
    assert response.json()['code'] == 'password_unchanged'
    assert client.get('/api/auth/me/').json()['user']['must_change_password']

def test_global_deactivation_during_password_change_cannot_reactivate_identity(world):
    from django.db import connections
    from apps.accounts.models import LoginIdentity
    client=world.login('a','doctor');token=client.get('/api/auth/csrf/').json()['csrf_token']
    changed=False;identity_id=world.accounts['a','doctor'].identity_id
    def deactivate_after_read(execute,statement,params,many,context):
        nonlocal changed
        result=execute(statement,params,many,context)
        if not changed and statement.startswith('SELECT') and 'FROM "accounts_loginidentity"' in statement:
            changed=True;LoginIdentity.objects.using('migration').filter(id=identity_id).update(is_active=False)
        return result
    with connections['control'].execute_wrapper(deactivate_after_read):
        response=client.post('/api/auth/change-password/',{'old_password':world.password,'new_password':'Another-Strong-Password-2026!'},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code==401
    identity=LoginIdentity.objects.using('control').get(id=identity_id)
    assert not identity.is_active and identity.check_password(world.password)

def test_legacy_login_routes_removed(world):
    from rest_framework.test import APIClient
    client=APIClient()
    for path in ['tenant-login','platform-login']:
        assert world.post(client,f'/api/auth/{path}/',{'username':'admin','password':world.password,'tenant':'a'}).status_code==404

def test_legacy_session_and_password_rejected(world):
    from rest_framework.test import APIClient
    account=world.accounts['a','tenant_admin'];client=APIClient();session=client.session
    session['identity']={'account_id':str(account.id),'tenant_id':str(account.tenant_id),'auth_hash':account.get_session_auth_hash()};session.save()
    assert client.get('/api/auth/me/').status_code==401
    assert not account.has_usable_password()

def test_runtime_member_insert_requires_identity(world):
    import psycopg,uuid
    for dsn,role in [(world.app_dsn,'doctor'),(world.control_dsn,'tenant_admin')]:
        with psycopg.connect(dsn) as conn:
            conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
            with __import__('pytest').raises(psycopg.errors.CheckViolation):
                conn.execute("INSERT INTO accounts_account(id,tenant_id,username,name,password,role,is_active,must_change_password,revision,created_at) VALUES(%s,%s,%s,'新成员','!',%s,true,false,1,now())",[uuid.uuid4(),world.tenants['a'].id,uuid.uuid4().hex,role])

def test_runtime_cannot_rebind_member_identity(world):
    import psycopg,pytest
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
        with pytest.raises(psycopg.errors.CheckViolation):conn.execute('UPDATE accounts_account SET identity_id=%s WHERE id=%s',[world.accounts['b','tenant_admin'].identity_id,world.accounts['a','doctor'].id])
