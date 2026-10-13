from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Account
from apps.tenants.services import validate_initial_password
from apps.tenants.quota import mutate_with_quota
from apps.core.context import tenant_transaction
from apps.core.permissions import require_role,require_tenant
from apps.core.helpers import ensure_revision,get_object
from apps.core.audit import audit
from apps.core.errors import ApiError
from .models import Doctor

BASIC_FIELDS=['name','phone','organization','department','title']
def visible_doctors(actor,include_deleted=False):
    require_tenant(actor)
    query=Doctor.objects.select_related('account').filter(tenant_id=actor.tenant_id)
    if not include_deleted:query=query.filter(deleted_at__isnull=True)
    if actor.role=='doctor':query=query.filter(id=actor.doctor_id)
    return query

def create_doctor(actor,data):
    require_tenant(actor);require_role(actor,'tenant_admin')
    if not data.get('username') or not data.get('password'):
        raise ApiError('validation_error','请填写医生账号和初始密码',status=400)
    validate_initial_password(data['password'])
    def mutation():
        account=Account(tenant_id=actor.tenant_id,username=data['username'],name=data['name'],role='doctor',is_active=data.get('enabled',True),must_change_password=True)
        account.set_password(data['password']);account.save()
        doctor=Doctor.objects.create(tenant_id=actor.tenant_id,account=account,**{k:data[k] for k in BASIC_FIELDS if k in data})
        account.doctor_id=doctor.id;account.save(update_fields=['doctor_id'])
        audit(actor,'create','doctor',doctor.id,{'name':doctor.name,'username':account.username})
        return doctor
    return mutate_with_quota(actor,'doctors',mutation)

def update_doctor(actor,doctor_id,data,expected_revision):
    require_tenant(actor)
    allowed=set(BASIC_FIELDS)|({'username','password','enabled'} if actor.role=='tenant_admin' else set())
    if set(data)-allowed:
        raise ApiError('forbidden_fields','包含不可修改的字段',{k:['不可修改'] for k in set(data)-allowed},400)
    with tenant_transaction(actor.tenant_id):
        doctor=get_object(visible_doctors(actor),doctor_id,True);ensure_revision(doctor,expected_revision)
        for field in BASIC_FIELDS:
            if field in data:setattr(doctor,field,data[field])
        account=doctor.account
        account.name=doctor.name
        if 'username' in data:account.username=data['username']
        if 'enabled' in data:account.is_active=data['enabled']
        if data.get('password'):
            validate_initial_password(data['password']);account.set_password(data['password']);account.must_change_password=True
        account.revision+=1;account.save()
        doctor.revision+=1;doctor.save()
        audit(actor,'update','doctor',doctor.id,{k:v for k,v in data.items() if k!='password'})
        return doctor

def set_doctor_enabled(actor,doctor_id,enabled,expected_revision):
    require_role(actor,'tenant_admin')
    return update_doctor(actor,doctor_id,{'enabled':enabled},expected_revision)

def delete_doctor(actor,doctor_id,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    def mutation():
        doctor=get_object(visible_doctors(actor),doctor_id,True);ensure_revision(doctor,expected_revision)
        from apps.patients.models import PatientDoctor
        if PatientDoctor.objects.filter(doctor=doctor,patient__deleted_at__isnull=True).exists():
            raise ApiError('doctor_has_patients','请先转交该医生负责的患者')
        doctor.deleted_at=timezone.now();doctor.revision+=1;doctor.save()
        account=doctor.account;account.is_active=False;account.revision+=1;account.save()
        audit(actor,'delete','doctor',doctor.id,{'name':doctor.name})
        return doctor
    return mutate_with_quota(actor,'doctors',mutation,delta=-1)

def restore_doctor(actor,doctor_id,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    def mutation():
        doctor=get_object(visible_doctors(actor,True).filter(deleted_at__isnull=False),doctor_id,True);ensure_revision(doctor,expected_revision)
        doctor.deleted_at=None;doctor.revision+=1;doctor.save()
        audit(actor,'restore','doctor',doctor.id,{'name':doctor.name})
        return doctor
    return mutate_with_quota(actor,'doctors',mutation)
