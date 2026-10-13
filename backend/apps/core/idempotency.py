import hashlib
import json
from contextlib import nullcontext
from django.db import transaction,connections
from apps.accounts.models import Account
from apps.tenants.models import Tenant
from .context import tenant_transaction
from .errors import ApiError
from .models import OperationReceipt

def run_idempotent(actor,key,operation,payload,mutation):
    if not key or len(key)>128:
        raise ApiError('idempotency_key_required','请提供有效的操作重试标识',status=400)
    alias='control' if actor.tenant_id is None else 'default'
    scope=tenant_transaction(actor.tenant_id) if actor.tenant_id else transaction.atomic(using=alias)
    with scope:
        if not Account.objects.using(alias).filter(id=actor.account_id,is_active=True,role=actor.role).exists() or (actor.tenant_id and not Tenant.objects.using(alias).filter(id=actor.tenant_id,enabled=True).exists()):
            raise ApiError('session_unavailable','账号或租户已停用',status=401)
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()).hexdigest()
        lock_id=int.from_bytes(hashlib.sha256(f'{actor.account_id}:{key}'.encode()).digest()[:8],'big',signed=True)
        with connections[alias].cursor() as cur:cur.execute('SELECT pg_advisory_xact_lock(%s)',[lock_id])
        old=OperationReceipt.objects.using(alias).filter(actor_id=actor.account_id,key=key).first()
        if old:
            if old.operation!=operation or old.payload_digest!=digest:
                raise ApiError('idempotency_key_reused','该重试标识已用于不同操作，请刷新后重试')
            return old.result
        result=mutation()
        OperationReceipt.objects.using(alias).create(tenant_id=actor.tenant_id,actor_id=actor.account_id,key=key,operation=operation,payload_digest=digest,result=result)
        return result
