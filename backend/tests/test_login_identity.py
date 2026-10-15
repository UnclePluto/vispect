import pytest
import psycopg
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError

@pytest.mark.parametrize('value',['13800000001','+86 138-0000-0001',' 0086 138-0000-0001 '])
def test_phone_normalization(value):
    from apps.accounts.phone import normalize_phone
    assert normalize_phone(value)=='+8613800000001'

@pytest.mark.parametrize('value',['','123','+1 13800000001','１２３８０００００００１',None])
def test_phone_rejects_invalid_input(value):
    from apps.accounts.phone import normalize_phone
    with pytest.raises(ApiError) as exc:normalize_phone(value)
    assert exc.value.status==400

def test_identity_database_privileges(world):
    from apps.accounts.identity_store import ensure_identity,probe_phone
    actor=world.actor('a','tenant_admin')
    with tenant_transaction(actor.tenant_id):
        identity,created=ensure_identity(actor,'13800000001',world.password,'统一用户',using='default')
        again,second=ensure_identity(actor,'008613800000001','Other-Strong-Password-2026!','不覆盖姓名',using='default')
        assert created and not second and identity.id==again.id
        assert probe_phone(actor,'13800000001')=={'phone':'+8613800000001','registered':True}
    from apps.accounts.models import LoginIdentity
    saved=LoginIdentity.objects.using('control').get(id=identity.id)
    assert saved.check_password(world.password) and saved.name=='统一用户'
    with psycopg.connect(world.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):conn.execute('SELECT password FROM accounts_loginidentity')
    with psycopg.connect(world.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):conn.execute('SELECT * FROM vispect_identity_workspaces(%s)',[identity.id])
    with pytest.raises(ApiError):probe_phone(world.actor('a','doctor'),'13800000001')
    with pytest.raises(ApiError):probe_phone(actor,'13800000001')

def test_member_projection_scope(world):
    from apps.accounts.identity_store import identity_workspaces,member_phone
    shared=world.bind_identity(world.accounts['a','tenant_admin'],'13800000001')
    world.bind_identity(world.accounts['b','doctor'],'13800000001')
    world.bind_identity(world.accounts['b','tenant_admin'],'13800000002')
    options=identity_workspaces(shared.id)
    assert {str(o['account_id']) for o in options}=={str(world.accounts['a','tenant_admin'].id),str(world.accounts['b','doctor'].id)}
    assert all('password' not in o for o in options)
    actor=world.actor('a','tenant_admin')
    with tenant_transaction(actor.tenant_id):
        assert member_phone(actor,actor.account_id)=='+8613800000001'
        with pytest.raises(ApiError):member_phone(actor,world.accounts['b','doctor'].id)
    with psycopg.connect(world.control_dsn) as conn:
        assert conn.execute("SELECT current_setting('vispect.identity_id',true)").fetchone()[0] in [None,'']
