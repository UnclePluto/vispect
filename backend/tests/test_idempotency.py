import pytest
from apps.core.errors import ApiError

def test_reused_key_with_different_payload(world):
    from apps.core.idempotency import run_idempotent
    from apps.core.audit import audit
    from apps.core.models import AuditEvent
    actor=world.actor('a','tenant_admin')
    def mutation():
        audit(actor,'test_action','tenant',actor.tenant_id,{'value':1})
        return {'result':1}
    first=run_idempotent(actor,'retry-1','test',{'value':1},mutation)
    second=run_idempotent(actor,'retry-1','test',{'value':1},mutation)
    assert first == second == {'result':1}
    with world.owner_context(actor.tenant_id):
        assert AuditEvent.objects.using('migration').filter(action='test_action').count() == 1
    with pytest.raises(ApiError) as exc:
        run_idempotent(actor,'retry-1','test',{'value':2},mutation)
    assert exc.value.code == 'idempotency_key_reused'

def test_deactivated_actor_cannot_read_old_receipt(world):
    from apps.core.idempotency import run_idempotent
    actor=world.actor('a','tenant_admin')
    run_idempotent(actor,'retry-2','test',{},lambda:{'value':'保密结果'})
    account=world.accounts['a','tenant_admin'];account.is_active=False;world.owner_save(account)
    with pytest.raises(ApiError) as exc:
        run_idempotent(actor,'retry-2','test',{},lambda:{})
    assert exc.value.status == 401
