from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.accounts.models import Account
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
    if not data.get('admin_username') or not data.get('admin_password'):
        raise ApiError('validation_error','请设置初始管理员账号和密码',status=400)
    validate_initial_password(data['admin_password'])
    with transaction.atomic(using='control'):
        tenant=Tenant.objects.using('control').create(slug=data['slug'],name=data['name'],enabled=data.get('enabled',True))
        limits=data.get('limits',{'doctors':100,'patients':1000,'studies':100})
        TenantQuota.objects.using('control').create(tenant=tenant,**{f'{r}_limit':limits[r] for r in RESOURCES})
        account=Account(tenant=tenant,username=data['admin_username'],name=data['admin_username'],role='tenant_admin',must_change_password=True)
        account.set_password(data['admin_password']);account.save(using='control')
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
                if resource not in RESOURCES or not isinstance(limit,int) or isinstance(limit,bool) or limit<0:
                    raise ApiError('validation_error','数量上限必须为非负整数',status=400)
                if limit<getattr(quota,f'{resource}_used'):
                    raise ApiError('quota_below_usage','数量上限不能低于当前使用量')
                setattr(quota,f'{resource}_limit',limit)
            quota.save(using='control')
        for field in ['name','slug','enabled']:
            if field in data:setattr(tenant,field,data[field])
        tenant.revision+=1;tenant.save(using='control')
        audit(actor,'update_tenant','tenant',tenant.id,{k:v for k,v in data.items() if k in ['name','slug','enabled','limits']})
        return Tenant.objects.using('control').select_related('quota').get(id=tenant.id)

def configure_administrator(actor,tenant_id,data):
    require_role(actor,'platform_admin')
    with transaction.atomic(using='control'):
        tenant=get_object(Tenant.objects.using('control'),tenant_id,True,no_key=True)
        account=Account.objects.using('control').select_for_update().filter(tenant=tenant,role='tenant_admin').order_by('created_at').first()
        if not account:raise ApiError('object_unavailable','管理员账号不可用',status=404)
        ensure_revision(account,data['expected_revision'])
        account.username=data['username'];account.name=data['name'];account.is_active=data.get('enabled',account.is_active)
        if data.get('password'):
            validate_initial_password(data['password']);account.set_password(data['password']);account.must_change_password=True
        account.revision+=1;account.save(using='control')
        audit(actor,'configure_administrator','account',account.id,{'username':account.username,'enabled':account.is_active})
        return account
