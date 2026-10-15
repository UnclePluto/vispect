from uuid import UUID
from django.db import transaction
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare
from apps.accounts.models import Account
from apps.tenants.models import Tenant
from .types import Actor
from .context import tenant_transaction
from .errors import ApiError

class TenantContextMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        request.actor=None
        if request.session.get('principal'):
            return self.unified_response(request)
        identity=request.session.get('identity')
        if not identity:
            return self.get_response(request)
        try:
            tenant_id=UUID(identity['tenant_id']) if identity.get('tenant_id') else None
            if tenant_id:
                if not Tenant.objects.using('control').filter(id=tenant_id,enabled=True).exists():
                    raise ApiError('session_unavailable','账号或租户已停用，请重新登录',status=401)
                with tenant_transaction(tenant_id):
                    return self.authenticated_response(request,identity,'default')
            with transaction.atomic(using='control'):
                return self.authenticated_response(request,identity,'control')
        except (ApiError,ValueError,KeyError) as exc:
            if not isinstance(exc,ApiError) or exc.status == 401:
                request.session.flush()
            if request.path in ['/api/auth/csrf/','/api/auth/tenant-login/','/api/auth/platform-login/','/api/auth/logout/']:
                return self.get_response(request)
            if not isinstance(exc,ApiError):
                exc=ApiError('unauthenticated','会话已失效，请重新登录',status=401)
            return JsonResponse({'code':exc.code,'message':exc.message,'fields':exc.fields},status=exc.status)

    def authenticated_response(self,request,identity,alias):
        account=Account.objects.using(alias).filter(id=identity['account_id'],is_active=True).first()
        if not account or not constant_time_compare(account.get_session_auth_hash(),identity.get('auth_hash','')):
            raise ApiError('session_unavailable','会话已失效，请重新登录',status=401)
        if alias == 'control' and account.role != 'platform_admin':
            raise ApiError('unauthenticated','会话已失效，请重新登录',status=401)
        request.account=account
        request.actor=Actor(account.id,account.tenant_id,account.role,account.doctor_id)
        if account.must_change_password and request.method not in ['GET','HEAD','OPTIONS'] and request.path not in ['/api/auth/change-password/','/api/auth/logout/']:
            raise ApiError('password_change_required','请先修改初始密码',status=403)
        return self.get_response(request)

    def unified_response(self,request):
        from apps.accounts.principal import load_principal
        from apps.accounts.session_context import current_workspace
        try:
            load_principal(request)
            if request.path.startswith('/api/auth/') or request.path=='/api/health/':return self.get_response(request)
            if request.login_identity.must_change_password:raise ApiError('password_change_required','请先修改初始密码',status=403)
            had_workspace=bool(request.login_context.active_account_id)
            workspace=current_workspace(request)
            if not workspace:raise ApiError('workspace_unavailable' if had_workspace else 'workspace_required','请先选择可用机构',status=409 if had_workspace else 403)
            tenant=workspace['tenant'];alias='default' if tenant else 'control'
            scope=tenant_transaction(tenant['id']) if tenant else transaction.atomic(using='control')
            with scope:
                account=Account.objects.using(alias).filter(id=workspace['account_id'],identity_id=request.login_identity.id,is_active=True).first()
                if not account:raise ApiError('workspace_unavailable','当前机构身份不可用，请重新选择',status=409)
                request.account=account;request.actor=Actor(account.id,account.tenant_id,account.role,account.doctor_id)
                return self.get_response(request)
        except (ApiError,ValueError,KeyError) as exc:
            if not isinstance(exc,ApiError):exc=ApiError('session_unavailable','登录已失效，请重新登录',status=401)
            if exc.status==401:
                request.session.flush()
                if request.path in ['/api/auth/login/','/api/auth/csrf/','/api/auth/logout/']:return self.get_response(request)
            return JsonResponse({'code':exc.code,'message':exc.message,'fields':exc.fields},status=exc.status)
