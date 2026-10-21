from rest_framework.permissions import BasePermission
from apps.core.errors import ApiError

class PatientPermission(BasePermission):
    def has_permission(self,request,view):
        if not getattr(request._request,'patient_principal',None):raise ApiError('unauthenticated','请先登录患者账号',status=401)
        return True
