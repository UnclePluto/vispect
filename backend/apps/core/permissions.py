from rest_framework.permissions import BasePermission
from .context import current_actor
from .errors import ApiError

def require_tenant(actor):
    if actor.tenant_id is None or actor.role == 'platform_admin':
        raise ApiError('forbidden','当前身份不能访问租户业务',status=403)
    return actor

def require_role(actor, *roles):
    if actor.role not in roles:
        raise ApiError('forbidden','没有执行此操作的权限',status=403)

class ActorPermission(BasePermission):
    def has_permission(self,request,view):
        current_actor(request)
        return True
