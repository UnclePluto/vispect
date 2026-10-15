import pytest
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError

def groups_for(world):
    return [{'phone':'13800000001','primary_account_id':str(world.accounts['a','tenant_admin'].id),'account_ids':[str(world.accounts['a','tenant_admin'].id),str(world.accounts['b','doctor'].id)],'enabled':True}]

def test_mapping_preserves_history_and_primary_password(world):
    from apps.accounts.migration_mapping import apply_mapping,preflight_mapping
    from apps.accounts.models import Account,LoginIdentity
    from apps.core.models import AuditEvent
    from apps.patients.services import create_patient
    a=world.accounts['a','tenant_admin'];b=world.accounts['b','doctor'];b.set_password('Secondary-Strong-Password-2026!');b.is_active=False;world.owner_save(b)
    create_patient(world.actor('a','tenant_admin'),{'name':'迁移前历史','code':'mapping-history','doctor_ids':[world.accounts['a','doctor'].doctor_id]})
    with tenant_transaction(a.tenant_id):before=list(AuditEvent.objects.values_list('id','actor_id'))
    assert preflight_mapping(groups_for(world))['valid']
    result=apply_mapping(groups_for(world));assert result['applied_groups']==1
    identity=LoginIdentity.objects.using('control').get(phone='+8613800000001');assert identity.check_password(world.password)
    for old in [a,b]:
        with world.owner_context(old.tenant_id):
            account=Account.objects.using('migration').get(id=old.id)
            assert account.identity_id==identity.id and not account.has_usable_password()
            assert account.is_active==old.is_active
    with tenant_transaction(a.tenant_id):assert list(AuditEvent.objects.values_list('id','actor_id'))==before

def test_mapping_conflict_rolls_back_every_group(world):
    from apps.accounts.migration_mapping import preflight_mapping,apply_mapping
    from apps.accounts.models import LoginIdentity
    groups=groups_for(world)+[{'phone':'13800000002','primary_account_id':str(world.accounts['a','doctor'].id),'account_ids':[str(world.accounts['a','doctor'].id),str(world.accounts['a','tenant_admin'].id)],'enabled':True}]
    report=preflight_mapping(groups);assert not report['valid'] and report['conflicts']
    with pytest.raises(ApiError):apply_mapping(groups)
    assert LoginIdentity.objects.using('control').count()==0

def test_mapping_rerun_preserves_new_password(world):
    from apps.accounts.migration_mapping import apply_mapping,preflight_mapping
    from apps.accounts.models import LoginIdentity
    apply_mapping(groups_for(world));identity=LoginIdentity.objects.using('control').get()
    identity.set_password('After-Migration-Strong-Password!');identity.save(using='control')
    assert apply_mapping(groups_for(world))['skipped_groups']==1
    assert LoginIdentity.objects.using('control').get().check_password('After-Migration-Strong-Password!')
    assert set(preflight_mapping(groups_for(world))['unmapped_account_ids'])=={str(world.accounts['a','doctor'].id),str(world.accounts['b','tenant_admin'].id),str(world.accounts[None,'platform_admin'].id)}

@pytest.mark.parametrize('change',[{'phone':'bad'}, {'primary_account_id':'invalid'}, {'enabled':'true'}, {'account_ids':[]}])
def test_mapping_invalid_input_is_reported(world,change):
    from apps.accounts.migration_mapping import preflight_mapping
    groups=groups_for(world);groups[0].update(change)
    assert not preflight_mapping(groups)['valid']

def test_mapping_preflight_cli_does_not_apply(world,tmp_path):
    import io,json
    from django.core.management import call_command
    from apps.accounts.models import LoginIdentity
    path=tmp_path/'mapping.json';path.write_text(json.dumps({'groups':groups_for(world)}))
    output=io.StringIO();call_command('migrate_login_identities',mapping=str(path),stdout=output)
    assert LoginIdentity.objects.using('control').count()==0
    assert world.password not in output.getvalue() and world.accounts['a','tenant_admin'].password not in output.getvalue()
