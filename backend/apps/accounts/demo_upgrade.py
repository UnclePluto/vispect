"""仅识别带完整演示标记和固定旧账号名称的已知虚构数据。"""
from django.db import transaction,connections
from apps.tenants.models import Tenant
from apps.core.models import AuditEvent
from .migration_mapping import _accounts,preflight_mapping

DEMO_PHONES={('demo-a','admin'):'19900001001',('demo-a','doctor1'):'19900001003',('demo-a','doctor2'):'19900001004',('demo-b','admin'):'19900001002',('demo-b','doctor1'):'19900001001',('demo-b','doctor2'):'19900001005',(None,'platform'):'19900001000'}

def demo_identity_mapping():
    accounts=_accounts();tenants={t.id:t for t in Tenant.objects.using('migration').filter(slug__in=['demo-a','demo-b'])};marked=set()
    with transaction.atomic(using='migration'):
        with connections['migration'].cursor() as cursor:
            cursor.execute("SELECT current_setting('vispect.tenant_id',true)");previous=cursor.fetchone()[0]
            try:
                for tenant in tenants.values():
                    cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant.id)])
                    if AuditEvent.objects.using('migration').filter(action='seed_demo_complete',object_id=tenant.id).exists():marked.add(tenant.slug)
            finally:cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[previous or ''])
    slots={};conflicts=[]
    for account in accounts.values():
        slug=tenants[account.tenant_id].slug if account.tenant_id in tenants else None
        key=(slug,account.username)
        if key not in DEMO_PHONES:continue
        if account.tenant_id is None:
            if account.role!='platform_admin' or marked!={'demo-a','demo-b'}:continue
        elif account.tenant_id not in tenants or slug not in marked:continue
        expected='platform_admin' if slug is None else 'tenant_admin' if account.username=='admin' else 'doctor'
        if account.role!=expected:continue
        if key in slots:conflicts.append({'code':'duplicate_demo_slot','account_ids':[str(slots[key].id),str(account.id)],'message':'演示账号槽位不唯一'})
        else:slots[key]=account
    groups={}
    for key,account in slots.items():
        phone=DEMO_PHONES[key];group=groups.setdefault(phone,{'phone':phone,'account_ids':[],'primary_account_id':str(account.id),'enabled':True})
        group['account_ids'].append(str(account.id))
        if key==('demo-a','admin'):group['primary_account_id']=str(account.id)
    # The shared identity must never take doctor1's password when its approved master is missing.
    if groups and set(slots)!=set(DEMO_PHONES):conflicts.append({'code':'incomplete_demo','account_ids':[],'message':'演示标记或固定账号不完整，拒绝猜测主账号'})
    report=preflight_mapping(list(groups.values()));report['conflicts'].extend(conflicts);report['valid']=not report['conflicts']
    report['legacy_unmapped_account_ids']=[id for id in report['unmapped_account_ids'] if accounts[id].identity_id is None]
    return report
