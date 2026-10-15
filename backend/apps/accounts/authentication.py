from rest_framework.authentication import BaseAuthentication,SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from apps.core.errors import ApiError

class SessionActorAuthentication(BaseAuthentication):
    def authenticate(self,request):
        if request.method not in ['GET','HEAD','OPTIONS']:
            try:
                SessionAuthentication().enforce_csrf(request)
            except PermissionDenied:
                raise ApiError('csrf_failed','请求校验失效，请刷新后重试',status=403)
        actor=getattr(request._request,'actor',None)
        if actor:
            return request._request.account,actor
        if getattr(request._request,'principal',None):return request._request.login_identity,request._request.principal
        return None

    def authenticate_header(self,request):
        return 'Session'
