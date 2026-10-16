from rest_framework.authentication import BaseAuthentication,SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from apps.core.errors import ApiError

class PatientSessionAuthentication(BaseAuthentication):
    def authenticate(self,request):
        if request.method not in ['GET','HEAD','OPTIONS']:
            try:SessionAuthentication().enforce_csrf(request)
            except PermissionDenied as exc:raise ApiError('csrf_failed','请求校验失效，请刷新后重试',status=403) from exc
        principal=getattr(request._request,'patient_principal',None)
        return (request._request.patient_identity,principal) if principal else None
    def authenticate_header(self,request):return 'PatientSession'
