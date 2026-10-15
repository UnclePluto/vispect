from contextlib import contextmanager
from django.db import transaction, connection
from .types import Actor
from .errors import ApiError

@contextmanager
def tenant_transaction(tenant_id):
    if tenant_id is None:
        raise ApiError('tenant_required','当前身份不能访问机构业务',status=403)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant_id)])
        yield

def current_actor(request) -> Actor:
    actor = getattr(request,'actor',None)
    if actor is None:
        raise ApiError('unauthenticated','请先登录',status=401)
    return actor
