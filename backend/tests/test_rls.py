import pytest
import psycopg
import uuid
from psycopg import sql

def test_cross_tenant_account_rows_are_invisible(world):
    assert world.runtime_rows('a','accounts_account') == world.account_ids('a')
    assert world.runtime_rows('b','accounts_account') == world.account_ids('b')

def test_missing_context_denies_rows(world):
    with psycopg.connect(world.app_dsn) as conn:
        assert conn.execute('SELECT id FROM accounts_account').fetchall() == []

def test_missing_context_denies_inserts(world):
    with psycopg.connect(world.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("INSERT INTO accounts_account (id,tenant_id,username,name,password,role,is_active,must_change_password,revision,created_at) VALUES (%s,%s,'unscoped','测试','unused','doctor',true,false,1,now())",[uuid.uuid4(),world.tenants['a'].id])

def test_cross_tenant_write_is_rejected(world):
    with psycopg.connect(world.app_dsn) as conn:
        with conn.transaction():
            conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute('UPDATE accounts_account SET tenant_id=%s WHERE id=%s',[world.tenants['b'].id,world.accounts['a','tenant_admin'].id])

@pytest.mark.parametrize('rollback',[False,True])
def test_reused_connection_does_not_inherit_context(world,rollback):
    with psycopg.connect(world.app_dsn,autocommit=True) as conn:
        try:
            with conn.transaction():
                conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
                assert sorted(r[0] for r in conn.execute('SELECT id FROM accounts_account')) == world.account_ids('a')
                if rollback:raise RuntimeError('模拟事务回滚')
        except RuntimeError:pass
        assert conn.execute('SELECT id FROM accounts_account').fetchall() == []
        with conn.transaction():
            conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['b'].id)])
            assert sorted(r[0] for r in conn.execute('SELECT id FROM accounts_account')) == world.account_ids('b')

def test_account_table_forces_rls_and_is_not_owned_by_runtime(world):
    with psycopg.connect(world.app_dsn) as conn:
        assert conn.execute("SELECT relrowsecurity,relforcerowsecurity,pg_get_userbyid(relowner)<>current_user FROM pg_class WHERE relname='accounts_account'").fetchone() == (True,True,True)

def test_control_connection_cannot_read_tenant_doctor_accounts(world):
    with psycopg.connect(world.control_dsn) as conn:
        assert conn.execute("SELECT id FROM accounts_account WHERE role='doctor'").fetchall() == []

def test_runtime_can_check_migration_status_without_writing(world):
    import psycopg
    with psycopg.connect(world.app_dsn) as conn:
        assert conn.execute('SELECT count(*) FROM django_migrations').fetchone()[0]>0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("INSERT INTO django_migrations(app,name,applied) VALUES ('invalid','invalid',now())")
