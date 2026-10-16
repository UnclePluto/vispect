import secrets
import uuid
from contextlib import contextmanager
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from apps.accounts.phone import normalize_phone
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from apps.tenants.models import Tenant
from .models import PatientLoginIdentity,PatientSession,PatientFormEntry
from .scope_store import digest_token,resolve_entry_scope,resolve_session_scope,revoke_session_digest
from .session_locks import lock_patient_identity
from .types import PatientPrincipal
from .activity import record_patient_activity


def patient_cookie(request):return request.COOKIES.get(settings.PATIENT_SESSION_COOKIE_NAME,'')


def check_entry(entry_id):
    entry=PatientFormEntry.objects.filter(id=entry_id,enabled=True,deleted_at__isnull=True,binding__stage__study__deleted_at__isnull=True,binding__form_version__form__deleted_at__isnull=True).first()
    if not entry:raise ApiError('entry_unavailable','填写链接已失效，请联系医生',status=404)
    return entry


def authenticate_patient(entry_token,phone,password):
    tenant_id,entry_id=resolve_entry_scope(entry_token);phone=normalize_phone(phone)
    with tenant_transaction(tenant_id):
        check_entry(entry_id)
        identity=PatientLoginIdentity.objects.filter(phone=phone,is_active=True,deleted_at__isnull=True).first()
        if identity is None:
            make_password(password)
            raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
        if not identity.check_password(password) or not Tenant.objects.filter(id=tenant_id,enabled=True).exists():raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
        return identity


def auth_envelope(identity,context):
    return {'user':{'id':str(identity.id),'phone':identity.phone,'must_change_password':identity.must_change_password},'next':'change_password' if identity.must_change_password else 'ready','session_token':str(context.context_token)}


def start_patient_login(request,identity):
    old_raw=patient_cookie(request);old_scope=resolve_session_scope(old_raw)
    with tenant_transaction(identity.tenant_id):
        ids={identity.id}
        if old_scope:ids.add(old_scope[2])
        for identity_id in sorted(ids,key=str):lock_patient_identity(identity_id,exclusive=True)
        fresh=PatientLoginIdentity.objects.filter(id=identity.id,is_active=True,deleted_at__isnull=True).first()
        if not fresh or not constant_time_compare(fresh.password,identity.password) or not Tenant.objects.filter(id=identity.tenant_id,enabled=True).exists():raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
        # The entry can be disabled while password verification is running.
        token=getattr(request,'patient_entry_token',None)
        if token:
            scope=resolve_entry_scope(token)
            if scope[0]!=fresh.tenant_id:raise ApiError('entry_unavailable','填写链接已失效，请联系医生',status=404)
            check_entry(scope[1])
        if old_scope:revoke_session_digest(digest_token(old_raw))
        raw=secrets.token_urlsafe(32)
        context=PatientSession.objects.create(tenant_id=fresh.tenant_id,identity_id=fresh.id,credential_digest=digest_token(raw),credential_version=fresh.credential_version,expires_at=timezone.now()+timedelta(seconds=settings.SESSION_COOKIE_AGE))
        request.patient_cookie_value=raw
        principal=PatientPrincipal(fresh.tenant_id,fresh.id,context.id,context.context_token)
        record_patient_activity(principal,'login')
        return auth_envelope(fresh,context)


@contextmanager
def patient_transaction(request,*,require_changed_password=True,exclusive=False,check_token=True):
    raw=patient_cookie(request);scope=resolve_session_scope(raw)
    if not scope:raise ApiError('patient_session_unavailable','患者登录已失效，请重新登录',status=401)
    tenant_id,session_id,identity_id=scope
    with tenant_transaction(tenant_id):
        lock_patient_identity(identity_id,exclusive=exclusive)
        context=PatientSession.objects.filter(id=session_id,credential_digest=digest_token(raw),revoked=False,expires_at__gt=timezone.now()).first()
        identity=PatientLoginIdentity.objects.filter(id=identity_id,is_active=True,deleted_at__isnull=True).first()
        if not context or not identity or context.credential_version!=identity.credential_version or not Tenant.objects.filter(id=tenant_id,enabled=True).exists():raise ApiError('patient_session_unavailable','患者登录已失效，请重新登录',status=401)
        if check_token and request.headers.get('X-Patient-Session-Token')!=str(context.context_token):raise ApiError('patient_session_changed','患者账号已在其他页面变化，请重新加载',status=409)
        if require_changed_password and identity.must_change_password:raise ApiError('password_change_required','请先修改初始密码',status=403)
        principal=PatientPrincipal(tenant_id,identity_id,session_id,context.context_token)
        request.patient_principal=principal;request.patient_identity=identity;request.patient_session=context
        yield principal


def change_patient_password(request,old_password,new_password):
    with patient_transaction(request,require_changed_password=False,exclusive=True):
        identity=request.patient_identity;context=request.patient_session
        if not identity.check_password(old_password):raise ApiError('old_password_invalid','原密码不正确',status=400)
        if old_password==new_password:raise ApiError('password_unchanged','新密码不能与原密码相同',status=400)
        try:validate_password(new_password,identity)
        except ValidationError as exc:raise ApiError('validation_error','新密码不符合要求',{'new_password':list(exc.messages)},400) from exc
        identity.set_password(new_password);identity.must_change_password=False;identity.credential_version+=1;identity.revision+=1;identity.save()
        PatientSession.objects.filter(identity_id=identity.id).exclude(id=context.id).update(revoked=True)
        raw=secrets.token_urlsafe(32);context.credential_digest=digest_token(raw);context.context_token=uuid.uuid4();context.credential_version=identity.credential_version;context.save()
        request.patient_cookie_value=raw
        record_patient_activity(request.patient_principal,'change_password')
        return auth_envelope(identity,context)


def logout_patient(request):
    with patient_transaction(request,require_changed_password=False,exclusive=True):
        context=request.patient_session;context.revoked=True;context.save(update_fields=['revoked'])
        record_patient_activity(request.patient_principal,'logout')
