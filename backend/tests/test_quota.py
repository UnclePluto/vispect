import pytest
from django.db import transaction
from apps.core.errors import ApiError

def test_limit_cannot_be_lower_than_usage(world):
    from apps.tenants.models import TenantQuota
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a'])
    quota.doctors_used=1;world.owner_save(quota)
    client=world.login(None,'platform_admin')
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    response=client.patch(f"/api/platform/tenants/{world.tenants['a'].id}/",{'limits':{'doctors':0,'patients':10,'studies':3},'expected_revision':1},format='json',HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 409
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).doctors_limit == 100

def test_zero_quota_forbids_creation(world):
    from apps.tenants.models import TenantQuota
    from apps.tenants.quota import mutate_with_quota
    from apps.accounts.models import Account
    quota=TenantQuota.objects.using('migration').get(tenant=world.tenants['a'])
    quota.doctors_limit=0;world.owner_save(quota)
    with pytest.raises(ApiError) as exc:
        mutate_with_quota(world.actor('a','tenant_admin'),'doctors',lambda:Account.objects.create(tenant=world.tenants['a'],username='blocked',name='不能创建',role='doctor'))
    assert exc.value.code == 'quota_exceeded'
    with world.owner_context(world.tenants['a'].id):
        assert not Account.objects.using('migration').filter(username='blocked').exists()

def test_runtime_cannot_edit_usage_directly(world):
    import psycopg
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(world.tenants['a'].id)])
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute('UPDATE tenants_tenantquota SET doctors_used=99')

def test_tenant_cannot_execute_global_usage_function(world):
    import psycopg
    with psycopg.connect(world.app_dsn) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute('SELECT * FROM vispect_platform_usage()')
