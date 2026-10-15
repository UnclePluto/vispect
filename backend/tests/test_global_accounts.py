import pytest
from apps.accounts.models import LoginIdentity,LoginSessionContext,Account
from apps.core.errors import ApiError
from apps.tenants.services import create_tenant,configure_administrator
from apps.core.models import AuditEvent
from apps.core.audit import audit
from apps.tenants.models import Tenant

def test_global_account_admin_permissions(world):
    for slug,role in [('a','tenant_admin'),('a','doctor')]:
        client=world.login(slug,role)
        assert client.get('/api/platform/accounts/?phone='+world.phone_for('a','tenant_admin')).status_code==403
    client=world.login(None,'platform_admin')
    assert client.get('/api/platform/accounts/').status_code==400
    r=client.get('/api/platform/accounts/?phone='+world.phone_for('a','tenant_admin'))
    assert r.status_code==200 and r.json()['count']==1
    assert 'password' not in r.json()['results'][0]
    assert client.get('/api/patients/').status_code==403

def test_platform_reset_revokes_all_sessions(world):
    a=world.accounts['a','tenant_admin'];world.bind_identity(world.accounts['b','doctor'],world.phone_for('a','tenant_admin'))
    first=world.login('a','tenant_admin');second=world.login('b','doctor')
    platform=world.login(None,'platform_admin')
    r=world.post(platform,f'/api/platform/accounts/{a.identity_id}/reset-password/',{'new_password':'Reset-Strong-2026!','expected_revision':1})
    assert r.status_code==200 and r.json()['must_change_password']
    assert first.get('/api/auth/me/').status_code==401 and second.get('/api/auth/me/').status_code==401
    user=LoginIdentity.objects.using('control').get(id=a.identity_id);assert user.check_password('Reset-Strong-2026!')
    assert not LoginSessionContext.objects.using('control').filter(identity=user,revoked=False).exists()

def test_global_revision_conflict(world):
    identity=world.accounts['a','tenant_admin'].identity_id;client=world.login(None,'platform_admin')
    first=world.post(client,f'/api/platform/accounts/{identity}/enabled/',{'enabled':False,'expected_revision':1});assert first.status_code==200
    assert world.post(client,f'/api/platform/accounts/{identity}/enabled/',{'enabled':True,'expected_revision':1}).status_code==409
    assert not LoginIdentity.objects.using('control').get(id=identity).is_active

def test_replace_admin_preserves_historical_actor(world):
    old=world.accounts['a','tenant_admin'];actor=world.actor('a','tenant_admin');platform=world.actor(None,'platform_admin')
    from apps.core.context import tenant_transaction
    with tenant_transaction(actor.tenant_id):event=audit(actor,'before_replace','account',old.id,{})
    configured=configure_administrator(platform,old.tenant_id,{'phone':world.phone_for('b','tenant_admin'),'name':'新管理员','expected_tenant_revision':1,'expected_admin_id':old.id})
    assert configured['tenant_revision']==2 and configured['administrator']['id']!=str(old.id)
    with world.owner_context(old.tenant_id):
        old.refresh_from_db(using='migration');event.refresh_from_db(using='migration')
        assert not old.is_active and event.actor_id==old.id and old.identity_id==actor_identity(world)
    with pytest.raises(ApiError) as exc:configure_administrator(platform,old.tenant_id,{'phone':'13812000001','initial_password':world.password,'name':'并发更换','expected_tenant_revision':1,'expected_admin_id':old.id})
    assert exc.value.code=='revision_conflict'

def actor_identity(world):return world.accounts['a','tenant_admin'].identity_id

def test_existing_doctor_not_promoted_implicitly(world):
    with pytest.raises(ApiError) as exc:configure_administrator(world.actor(None,'platform_admin'),world.tenants['a'].id,{'phone':world.phone_for('a','doctor'),'name':'不可提权','expected_tenant_revision':1,'expected_admin_id':world.accounts['a','tenant_admin'].id})
    assert exc.value.code=='member_role_conflict'

def test_create_organization_rolls_back_identity(world,monkeypatch):
    from apps.tenants import services
    monkeypatch.setattr(services,'audit',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('audit failed')))
    with pytest.raises(RuntimeError):create_tenant(world.actor(None,'platform_admin'),{'slug':'rollback','name':'回滚','admin_phone':'13812000002','admin_initial_password':world.password})
    assert not Tenant.objects.using('control').filter(slug='rollback').exists()
    assert not LoginIdentity.objects.using('control').filter(phone='+8613812000002').exists()

def test_configure_disabled_admin_uses_tenant_revision(world):
    old=world.accounts['a','tenant_admin'];old.is_active=False;world.owner_save(old)
    p=world.login(None,'platform_admin')
    r=p.get(f'/api/platform/tenants/{old.tenant_id}/administrator/');assert r.status_code==200 and r.json()=={'tenant_revision':1,'administrator':None}
    r=configure_administrator(world.actor(None,'platform_admin'),old.tenant_id,{'phone':world.phone_for('a','tenant_admin'),'name':'恢复管理员','expected_tenant_revision':1,'expected_admin_id':None})
    assert r['administrator']['id']==str(old.id) and r['tenant_revision']==2
