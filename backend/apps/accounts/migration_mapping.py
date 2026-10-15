"""显式旧账号映射；仅管理连接使用，绝不通过姓名或联系方式推断身份。"""
from uuid import UUID
from django.db import connections,transaction
from apps.core.errors import ApiError
from apps.tenants.models import Tenant
from .models import Account,LoginIdentity
from .phone import normalize_phone

def _accounts(lock=False):
    result={}
    with transaction.atomic(using='migration'):
        with connections['migration'].cursor() as cursor:
            cursor.execute("SELECT current_setting('vispect.tenant_id',true)");previous=cursor.fetchone()[0]
            try:
                tenants=[None,*Tenant.objects.using('migration').order_by('id').values_list('id',flat=True)]
                for tenant_id in tenants:
                    cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant_id) if tenant_id else ''])
                    query=Account.objects.using('migration').filter(tenant_id=tenant_id).order_by('id')
                    if lock:query=query.select_for_update()
                    result.update({str(a.id):a for a in query})
            finally:cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[previous or ''])
    return result

def _preflight(groups,accounts):
    report={'valid':True,'groups':[],'conflicts':[],'unmapped_account_ids':[],'applied_groups':0,'skipped_groups':0}
    seen_accounts=set();seen_phones=set()
    def conflict(code,ids,message):report['conflicts'].append({'code':code,'account_ids':ids,'message':message})
    if not isinstance(groups,list):groups=[];conflict('invalid_mapping',[],'groups 必须是数组')
    for group in groups:
        if not isinstance(group,dict):conflict('invalid_mapping',[],'每组映射必须是对象');continue
        try:
            phone=normalize_phone(group.get('phone'))
            raw_ids=group.get('account_ids')
            if not isinstance(raw_ids,list) or not raw_ids:raise ValueError()
            ids=[str(UUID(str(value))) for value in raw_ids];primary=str(UUID(str(group.get('primary_account_id'))))
            enabled=group.get('enabled',True)
            if not isinstance(enabled,bool):raise ValueError()
        except (ApiError,ValueError,TypeError,AttributeError):
            conflict('invalid_mapping',[],'手机号、账号 ID、主账号或启用状态无效');continue
        if phone in seen_phones:conflict('duplicate_phone',ids,'同一手机号须在同一组定义且全局启用设置一致')
        seen_phones.add(phone)
        if len(set(ids))!=len(ids) or seen_accounts.intersection(ids):conflict('duplicate_account',ids,'账号重复出现在映射中')
        seen_accounts.update(ids)
        if primary not in ids:conflict('invalid_primary',ids,'主账号必须属于本组')
        if any(value not in accounts for value in ids):conflict('unknown_account',ids,'存在不可用账号');continue
        scopes=[accounts[value].tenant_id for value in ids]
        if len(scopes)!=len(set(scopes)):conflict('duplicate_organization',ids,'同一手机号在同一机构存在多条身份，请先明确处理')
        existing=LoginIdentity.objects.using('migration').filter(phone=phone).first()
        bindings={accounts[value].identity_id for value in ids if accounts[value].identity_id}
        if bindings and (not existing or bindings!={existing.id}):conflict('identity_mismatch',ids,'账号已经绑定其他统一身份')
        if existing and primary in accounts and accounts[primary].identity_id!=existing.id:
            conflict('existing_identity',ids,'手机号已注册，主账号须明确引用其现有成员，不能覆盖已有凭据')
        if not existing and primary in accounts and not accounts[primary].has_usable_password():conflict('unusable_primary_password',ids,'主账号没有可迁移密码')
        report['groups'].append({'phone':phone,'primary_account_id':primary,'account_ids':ids,'enabled':enabled})
    report['unmapped_account_ids']=sorted(set(accounts)-seen_accounts)
    report['valid']=not report['conflicts']
    return report

def preflight_mapping(groups):return _preflight(groups,_accounts())

def apply_mapping(groups):
    with transaction.atomic(using='migration'):
        accounts=_accounts(lock=True);report=_preflight(groups,accounts)
        if not report['valid']:raise ApiError('mapping_conflict','映射存在冲突，请先完成预检',status=409)
        with connections['migration'].cursor() as cursor:
            cursor.execute("SELECT current_setting('vispect.tenant_id',true)");previous=cursor.fetchone()[0]
            try:
                for group in report['groups']:
                    members=[accounts[value] for value in group['account_ids']]
                    identity=LoginIdentity.objects.using('migration').select_for_update().filter(phone=group['phone']).first()
                    if identity and all(a.identity_id==identity.id and not a.has_usable_password() for a in members):
                        report['skipped_groups']+=1;continue
                    if identity is None:
                        primary=accounts[group['primary_account_id']]
                        identity=LoginIdentity.objects.using('migration').create(phone=group['phone'],name=primary.name,password=primary.password,is_active=group['enabled'],must_change_password=any(a.must_change_password for a in members))
                    for account in members:
                        cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(account.tenant_id) if account.tenant_id else ''])
                        account.identity=identity;account.set_unusable_password();account.revision+=1
                        account.save(using='migration',update_fields=['identity','password','revision'])
                    report['applied_groups']+=1
            finally:cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[previous or ''])
        return report
