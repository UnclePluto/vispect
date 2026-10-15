from contextlib import contextmanager
import uuid
from django.db import transaction
from apps.core import workspace_lock
from apps.core.context import tenant_transaction
from apps.core.types import Actor
from apps.core.errors import ApiError
from .models import Account,LoginSessionContext
from .principal import get_principal,load_principal
from .identity_store import identity_workspaces
from .session_context import auth_envelope,current_workspace

@contextmanager
def workspace_transaction(request,*,using):
    principal=get_principal(request)
    with transaction.atomic(using=using):
        workspace_lock.lock_workspace_context(principal.context_id,using=using,exclusive=False)
        load_principal(request)
        if request.login_identity.must_change_password:raise ApiError('password_change_required','请先修改初始密码',status=403)
        had_workspace=bool(request.login_context.active_account_id)
        workspace=current_workspace(request)
        if not workspace:raise ApiError('workspace_unavailable' if had_workspace else 'workspace_required','请先选择可用机构',status=409 if had_workspace else 403)
        if request.headers.get('X-Workspace-Token')!=str(request.login_context.workspace_token):raise ApiError('workspace_changed','机构已切换，请重新加载当前空间',status=409)
        tenant=workspace['tenant'];alias='default' if tenant else 'control'
        scope=tenant_transaction(tenant['id']) if tenant else transaction.atomic(using='control')
        with scope:
            account=Account.objects.using(alias).filter(id=workspace['account_id'],identity_id=principal.user_id,is_active=True).first()
            if not account:raise ApiError('workspace_unavailable','当前机构身份不可用，请重新选择',status=409)
            actor=Actor(account.id,account.tenant_id,account.role,account.doctor_id)
            request.account=account;request.actor=actor
            yield actor

def switch_workspace(request,account_id,expected_token):
    principal=get_principal(request)
    with transaction.atomic(using='control'):
        workspace_lock.lock_workspace_context(principal.context_id,using='control',exclusive=True)
        load_principal(request)
        if request.login_identity.must_change_password:raise ApiError('password_change_required','请先修改初始密码',status=403)
        context=LoginSessionContext.objects.using('control').select_for_update().get(id=principal.context_id)
        if str(context.workspace_token)!=str(expected_token):raise ApiError('workspace_changed','机构已切换，请重新加载当前空间',status=409)
        if not any(w['account_id']==str(account_id) for w in identity_workspaces(principal.user_id)):raise ApiError('object_unavailable','目标机构不存在或当前不可访问',status=404)
        context.active_account_id=account_id;context.workspace_token=uuid.uuid4()
        context.save(using='control',update_fields=['active_account','workspace_token'])
        request.login_context=context
        return auth_envelope(request)
