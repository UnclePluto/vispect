from dataclasses import dataclass
from uuid import UUID
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connections,DatabaseError
from apps.core.errors import ApiError
from apps.core.permissions import require_role
from .phone import normalize_phone

@dataclass(frozen=True)
class LoginIdentityRef:
    id: UUID
    phone: str

def _call(using,statement,args):
    try:
        with connections[using].cursor() as cursor:
            cursor.execute(statement,args)
            return cursor.fetchall()
    except DatabaseError as exc:
        if getattr(exc.__cause__,'sqlstate',None)=='42501':
            raise ApiError('forbidden','没有管理登录身份的权限',status=403) from exc
        raise

def probe_phone(actor,phone,*,using=None):
    require_role(actor,'tenant_admin','platform_admin')
    phone=normalize_phone(phone);using=using or ('control' if actor.tenant_id is None else 'default')
    rows=_call(using,'SELECT vispect_probe_identity(%s,%s)',[actor.account_id,phone])
    return {'phone':phone,'registered':rows[0][0]}

def ensure_identity(actor,phone,initial_password,name,*,using):
    status=probe_phone(actor,phone,using=using);phone=status['phone'];password_hash=''
    if not status['registered']:
        if not initial_password:raise ApiError('validation_error','新手机号需要设置初始密码',{'initial_password':['请填写初始密码']},400)
        try:validate_password(initial_password)
        except ValidationError as exc:raise ApiError('validation_error','密码不符合要求',{'initial_password':list(exc.messages)},400) from exc
        password_hash=make_password(initial_password)
    rows=_call(using,'SELECT * FROM vispect_ensure_identity(%s,%s,%s,%s)',[actor.account_id,phone,password_hash,name])
    return LoginIdentityRef(rows[0][0],phone),rows[0][1]

def member_phone(actor,account_id):
    using='control' if actor.tenant_id is None else 'default'
    rows=_call(using,'SELECT vispect_member_phone(%s,%s)',[actor.account_id,account_id])
    if rows[0][0] is None:raise ApiError('object_unavailable','对象不存在或当前不可访问',status=404)
    return rows[0][0]

def identity_workspaces(identity_id):
    rows=_call('control','SELECT * FROM vispect_identity_workspaces(%s)',[identity_id])
    return [{'account_id':str(r[0]),'tenant':{'id':str(r[1]),'name':r[2],'slug':r[3]} if r[1] else None,'role':r[4],'name':r[5]} for r in rows]
