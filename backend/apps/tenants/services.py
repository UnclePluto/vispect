import uuid
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.accounts.models import Account
from apps.accounts.identity_store import ensure_identity,member_phone,_call
from apps.core.permissions import require_role
from apps.core.helpers import ensure_revision,get_object
from apps.core.errors import ApiError
from apps.core.audit import audit
from .models import Tenant,TenantQuota
from .quota import RESOURCES

def validate_initial_password(password):
    try:validate_password(password)
    except ValidationError as exc:raise ApiError('validation_error','密码不符合要求',{'password':list(exc.messages)},400)

def create_tenant(actor,data):
    require_role(actor,'platform_admin')
    with transaction.atomic(using='control'):
        tenant=Tenant.objects.using('control').create(slug=data['slug'],name=data['name'],enabled=data.get('enabled',True))
        limits=data.get('limits',{'doctors':100,'patients':1000,'studies':100})
        TenantQuota.objects.using('control').create(tenant=tenant,**{f'{r}_limit':limits[r] for r in RESOURCES})
        identity,_=ensure_identity(actor,data.get('admin_phone'),data.get('admin_initial_password'),data.get('admin_name',data['name']),using='control')
        account=Account(tenant=tenant,identity_id=identity.id,username=uuid.uuid4().hex,name=data.get('admin_name',data['name']),role='tenant_admin')
        account.set_unusable_password();account.save(using='control')
        audit(actor,'create_tenant','tenant',tenant.id,{'slug':tenant.slug,'name':tenant.name,'limits':limits})
        return Tenant.objects.using('control').select_related('quota').get(id=tenant.id)

def update_tenant(actor,tenant_id,data,expected_revision):
    require_role(actor,'platform_admin')
    with transaction.atomic(using='control'):
        tenant=get_object(Tenant.objects.using('control'),tenant_id,True,no_key=True)
        ensure_revision(tenant,expected_revision)
        quota=TenantQuota.objects.using('control').select_for_update().get(tenant=tenant)
        if 'limits' in data:
            for resource,limit in data['limits'].items():
                if resource not in RESOURCES or not isinstance(limit,int) or isinstance(limit,bool) or not 0<=limit<=2147483647:
                    raise ApiError('validation_error','数量上限必须为 0 至 2147483647 的整数',status=400)
                if limit<getattr(quota,f'{resource}_used'):
                    raise ApiError('quota_below_usage','数量上限不能低于当前使用量')
                setattr(quota,f'{resource}_limit',limit)
            quota.save(using='control')
        for field in ['name','slug','enabled']:
            if field in data:setattr(tenant,field,data[field])
        tenant.revision+=1;tenant.save(using='control')
        audit(actor,'update_tenant','tenant',tenant.id,{k:v for k,v in data.items() if k in ['name','slug','enabled','limits']})
        return Tenant.objects.using('control').select_related('quota').get(id=tenant.id)

def administrator_payload(actor,tenant):
    account=Account.objects.using('control').filter(tenant=tenant,role='tenant_admin',is_active=True).first()
    return {'tenant_revision':tenant.revision,'administrator':{'id':str(account.id),'login_phone':member_phone(actor,account.id),'name':account.name,'enabled':account.is_active,'revision':account.revision} if account else None}

def configure_administrator(actor,tenant_id,data):
    require_role(actor,'platform_admin')
    with transaction.atomic(using='control'):
        tenant=get_object(Tenant.objects.using('control'),tenant_id,True,no_key=True)
        ensure_revision(tenant,data['expected_tenant_revision'])
        current=Account.objects.using('control').select_for_update().filter(tenant=tenant,role='tenant_admin',is_active=True).first()
        if (str(current.id) if current else None)!=(str(data['expected_admin_id']) if data['expected_admin_id'] else None):
            raise ApiError('revision_conflict','管理员已变更，请刷新后重试')
        identity,_=ensure_identity(actor,data['phone'],data.get('initial_password'),data['name'],using='control')
        membership=_call('control','SELECT * FROM vispect_identity_membership(%s,%s,%s)',[actor.account_id,identity.id,tenant.id])
        if membership and membership[0][1]!='tenant_admin':raise ApiError('member_role_conflict','该手机号已是本机构医生，不能隐式转换管理员身份')
        target=Account.objects.using('control').select_for_update().filter(id=membership[0][0]).first() if membership else None
        if current and (target is None or current.id!=target.id):
            current.is_active=False;current.revision+=1;current.save(using='control',update_fields=['is_active','revision'])
        if target is None:
            target=Account(tenant=tenant,identity_id=identity.id,username=uuid.uuid4().hex,role='tenant_admin');target.set_unusable_password()
        target.name=data['name'];target.is_active=data.get('enabled',True);target.revision+=1;target.save(using='control')
        tenant.revision+=1;tenant.save(using='control',update_fields=['revision'])
        audit(actor,'configure_administrator','account',target.id,{'phone':identity.phone,'enabled':target.is_active,'previous_account_id':str(current.id) if current else None})
        return administrator_payload(actor,tenant)
