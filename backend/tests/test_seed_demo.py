from io import StringIO
from django.core.management import call_command
from apps.tenants.models import Tenant,TenantQuota
from apps.core.context import tenant_transaction

def test_seed_demo_is_repeatable(world,monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD',world.password)
    platform=world.accounts[None,'platform_admin'];platform.username='fixture-platform';world.owner_save(platform)
    from apps.doctors.models import Doctor
    from apps.patients.models import Patient
    from apps.forms.models import FormVersion
    from apps.studies.models import Study
    def counts():
        result=[]
        for t in Tenant.objects.using('control').filter(slug__startswith='demo-').order_by('slug'):
            with tenant_transaction(t.id):result.append((t.slug,Doctor.objects.count(),Patient.objects.count(),FormVersion.objects.count(),Study.objects.count()))
        return result
    call_command('seed_demo',stdout=StringIO());first=counts()
    from apps.accounts.models import Account
    from apps.core.types import Actor
    from apps.doctors.services import update_doctor
    t=Tenant.objects.using('control').get(slug='demo-a');admin=Account.objects.using('control').get(tenant=t,role='tenant_admin')
    from apps.accounts.models import LoginIdentity
    assert LoginIdentity.objects.using('control').get(id=admin.identity_id).must_change_password
    with tenant_transaction(t.id):doctor=Doctor.objects.get(account__username='doctor1');assert LoginIdentity.objects.using('control').get(id=doctor.account.identity_id).must_change_password
    update_doctor(Actor(admin.id,t.id,'tenant_admin',None),doctor.id,{'name':'保留的演示修改'},doctor.revision)
    call_command('seed_demo',stdout=StringIO());assert counts()==first and len(first)==2
    with tenant_transaction(t.id):assert Doctor.objects.get(id=doctor.id).name=='保留的演示修改'
    for slug,doctors,patients,versions,studies in first:
        assert doctors==2 and patients>=3 and versions>=3 and studies>=2
        quota=TenantQuota.objects.using('control').get(tenant__slug=slug);assert quota.doctors_used==2 and quota.studies_used==2

def test_seed_phone_identities_is_repeatable(world,monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD',world.password)
    platform=world.accounts[None,'platform_admin'];platform.username='fixture-platform';world.owner_save(platform)
    from apps.accounts.models import LoginIdentity
    from apps.accounts.demo_upgrade import demo_identity_mapping
    call_command('seed_demo',stdout=StringIO());report=demo_identity_mapping();assert report['valid']
    demo=LoginIdentity.objects.using('control').filter(phone__startswith='+86199000010')
    assert demo.count()==6
    hashes={str(i.id):i.password for i in demo};call_command('seed_demo',stdout=StringIO())
    assert hashes=={str(i.id):i.password for i in demo}
    assert any(len(g['account_ids'])==2 and g['phone']=='+8619900001001' for g in report['groups'])

def test_upgrade_existing_demo_keeps_password_and_ids(world,monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD',world.password)
    platform=world.accounts[None,'platform_admin'];platform.username='fixture-platform';world.owner_save(platform)
    call_command('seed_demo',stdout=StringIO())
    from apps.accounts.models import Account,LoginIdentity
    from apps.accounts.migration_mapping import _accounts,apply_mapping
    from apps.accounts.demo_upgrade import demo_identity_mapping
    demo_accounts=[a for a in _accounts().values() if a.username=='platform' or a.tenant_id in set(Tenant.objects.using('control').filter(slug__startswith='demo-').values_list('id',flat=True))]
    ids={a.id for a in demo_accounts};identity_ids={a.identity_id for a in demo_accounts}
    chosen_hash=None
    for a in demo_accounts:
        with world.owner_context(a.tenant_id):
            a.identity_id=None;a.set_password(world.password+'-Master' if a.username=='admin' and a.tenant_id==Tenant.objects.using('control').get(slug='demo-a').id else world.password)
            if a.username=='admin' and a.tenant_id==Tenant.objects.using('control').get(slug='demo-a').id:chosen_hash=a.password
            a.save(using='migration',update_fields=['identity','password'])
    LoginIdentity.objects.using('migration').filter(id__in=identity_ids).delete()
    report=demo_identity_mapping();assert report['valid'];assert report['legacy_unmapped_account_ids']==[]
    apply_mapping(report['groups']);shared=LoginIdentity.objects.using('control').get(phone='+8619900001001');assert shared.password==chosen_hash
    assert ids.issubset({a.id for a in _accounts().values()})
    shared.set_password(world.password+'-UserChanged');shared.save(using='control',update_fields=['password'])
    apply_mapping(demo_identity_mapping()['groups']);shared.refresh_from_db(using='control');assert shared.check_password(world.password+'-UserChanged')
