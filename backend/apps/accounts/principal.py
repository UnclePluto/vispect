from dataclasses import dataclass
from uuid import UUID
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from apps.core.errors import ApiError
from .models import LoginIdentity,LoginSessionContext

@dataclass(frozen=True)
class Principal:
    user_id: UUID
    context_id: UUID

def get_principal(request):
    principal=getattr(request,'principal',None)
    if principal is None:raise ApiError('unauthenticated','请先登录',status=401)
    return principal

def load_principal(request):
    data=request.session.get('principal',{})
    try:
        identity=LoginIdentity.objects.using('control').filter(id=UUID(data['user_id']),is_active=True).first()
        context=LoginSessionContext.objects.using('control').filter(id=UUID(data['context_id']),identity=identity,revoked=False,expires_at__gt=timezone.now()).first() if identity else None
        if not context or not constant_time_compare(identity.get_session_auth_hash(),data.get('auth_hash','')):raise ValueError()
    except (ValueError,KeyError,TypeError,AttributeError):
        raise ApiError('session_unavailable','登录已失效，请重新登录',status=401)
    request.login_identity=identity;request.login_context=context;request.principal=Principal(identity.id,context.id)
    return request.principal
