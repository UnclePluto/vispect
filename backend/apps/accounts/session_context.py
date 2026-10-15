from datetime import timedelta
import uuid
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from .models import Account,LoginIdentity,LoginSessionContext
from .identity_store import identity_workspaces
from .phone import normalize_phone
from .principal import get_principal
from .serializers import identity_payload

def authenticate_phone(phone,password):
    phone=normalize_phone(phone)
    identity=LoginIdentity.objects.using('control').filter(phone=phone).first()
    if identity is None:
        make_password(password)
        raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
    if not identity.check_password(password) or not identity.is_active:raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
    return identity

def bind_session(request,identity,context):
    request.session.pop('identity',None)
    request.session['principal']={'user_id':str(identity.id),'context_id':str(context.id),'auth_hash':identity.get_session_auth_hash()}
    request.login_identity=identity;request.login_context=context
    from .principal import Principal
    request.principal=Principal(identity.id,context.id)

def activate_single(identity,context):
    options=identity_workspaces(identity.id)
    if not identity.must_change_password and len(options)==1:
        context.active_account_id=options[0]['account_id'];context.save(using='control',update_fields=['active_account'])

def current_workspace(request,options=None):
    context=request.login_context
    if not context.active_account_id:return None
    options=identity_workspaces(request.login_identity.id) if options is None else options
    workspace=next((w for w in options if w['account_id']==str(context.active_account_id)),None)
    if workspace is None:
        LoginSessionContext.objects.using('control').filter(id=context.id,active_account_id=context.active_account_id,workspace_token=context.workspace_token).update(active_account_id=None,workspace_token=uuid.uuid4())
        context.refresh_from_db(using='control')
        workspace=next((w for w in options if w['account_id']==str(context.active_account_id)),None)
    return workspace

def actor_payload(request,workspace):
    if not workspace:return None
    tenant=workspace['tenant'];alias='default' if tenant else 'control'
    scope=tenant_transaction(tenant['id']) if tenant else transaction.atomic(using='control')
    with scope:
        account=Account.objects.using(alias).select_related('tenant').filter(id=workspace['account_id'],identity_id=request.login_identity.id,is_active=True).first()
        if not account:return None
        payload=identity_payload(account);payload['must_change_password']=request.login_identity.must_change_password
        return payload

def auth_envelope(request):
    get_principal(request);identity=request.login_identity;context=request.login_context
    options=identity_workspaces(identity.id);workspace=current_workspace(request,options)
    actor=None if identity.must_change_password else actor_payload(request,workspace)
    next_step='change_password' if identity.must_change_password else 'ready' if actor else 'choose_workspace' if options else 'no_workspace'
    return {'user':{'id':str(identity.id),'phone':identity.phone,'name':identity.name,'must_change_password':identity.must_change_password},'actor':actor,'workspaces':options,'workspace_token':str(context.workspace_token),'next':next_step}

def start_login(request,identity):
    with transaction.atomic(using='control'):
        fresh=LoginIdentity.objects.using('control').select_for_update().filter(id=identity.id,is_active=True).first()
        if not fresh or not constant_time_compare(fresh.get_session_auth_hash(),identity.get_session_auth_hash()):raise ApiError('credentials_invalid','手机号或密码不正确',status=401)
        context=LoginSessionContext.objects.using('control').create(identity=fresh,expires_at=timezone.now()+timedelta(seconds=settings.SESSION_COOKIE_AGE))
        activate_single(fresh,context);request.session.cycle_key();bind_session(request,fresh,context)
        return auth_envelope(request)

def change_identity_password(request,old_password,new_password):
    principal=get_principal(request)
    with transaction.atomic(using='control'):
        identity=LoginIdentity.objects.using('control').select_for_update().filter(id=principal.user_id,is_active=True).first()
        data=request.session.get('principal',{})
        context=LoginSessionContext.objects.using('control').select_for_update().filter(id=principal.context_id,identity=identity,revoked=False,expires_at__gt=timezone.now()).first() if identity else None
        if not context or not constant_time_compare(identity.get_session_auth_hash(),data.get('auth_hash','')):raise ApiError('session_unavailable','登录已失效，请重新登录',status=401)
        if not identity.check_password(old_password):raise ApiError('old_password_invalid','原密码不正确',status=400)
        if old_password==new_password:raise ApiError('password_unchanged','新密码不能与原密码相同',status=400)
        try:validate_password(new_password,identity)
        except ValidationError as exc:raise ApiError('validation_error','新密码不符合要求',{'new_password':list(exc.messages)},400) from exc
        identity.set_password(new_password);identity.must_change_password=False;identity.revision+=1
        identity.save(using='control',update_fields=['password','must_change_password','revision'])
        LoginSessionContext.objects.using('control').filter(identity=identity).exclude(id=context.id).update(revoked=True)
        activate_single(identity,context);request.session.cycle_key();bind_session(request,identity,context)
        return auth_envelope(request)
