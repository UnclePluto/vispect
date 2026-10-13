from io import StringIO
from django.core.management import call_command
from apps.tenants.models import Tenant,TenantQuota
from apps.core.context import tenant_transaction

def test_seed_demo_is_repeatable(world,monkeypatch):
    monkeypatch.setenv('DEMO_PASSWORD',world.password)
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
    assert admin.must_change_password
    with tenant_transaction(t.id):doctor=Doctor.objects.get(account__username='doctor1');assert doctor.account.must_change_password
    update_doctor(Actor(admin.id,t.id,'tenant_admin',None),doctor.id,{'name':'保留的演示修改'},doctor.revision)
    call_command('seed_demo',stdout=StringIO());assert counts()==first and len(first)==2
    with tenant_transaction(t.id):assert Doctor.objects.get(id=doctor.id).name=='保留的演示修改'
    for slug,doctors,patients,versions,studies in first:
        assert doctors==2 and patients>=3 and versions>=3 and studies>=2
        quota=TenantQuota.objects.using('control').get(tenant__slug=slug);assert quota.doctors_used==2 and quota.studies_used==2
