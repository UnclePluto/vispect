from django.http import JsonResponse
from .errors import ApiError

class TenantContextMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.path.startswith('/api/patient/'):return self.get_response(request)
        request.actor=None
        # Historical session payloads never authenticate a global identity.
        if not request.session.get('principal'):return self.get_response(request)
        from apps.accounts.principal import load_principal
        try:
            load_principal(request)
            if request.path.startswith('/api/auth/') or request.path=='/api/health/':return self.get_response(request)
            from apps.accounts.workspaces import workspace_transaction
            alias='control' if request.path.startswith('/api/platform/') else 'default'
            with workspace_transaction(request,using=alias):return self.get_response(request)
        except (ApiError,ValueError,KeyError) as exc:
            if not isinstance(exc,ApiError):exc=ApiError('session_unavailable','登录已失效，请重新登录',status=401)
            if exc.status==401:
                request.session.flush()
                if request.path in ['/api/auth/login/','/api/auth/csrf/','/api/auth/logout/']:return self.get_response(request)
            return JsonResponse({'code':exc.code,'message':exc.message,'fields':exc.fields},status=exc.status)
