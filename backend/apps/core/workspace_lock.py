import hashlib
from uuid import UUID
from django.db import connections

def workspace_lock_key(context_id):
    return int.from_bytes(hashlib.sha256(b'vispect.workspace:'+UUID(str(context_id)).bytes).digest()[:8],'big',signed=True)

def lock_workspace_context(context_id,*,using,exclusive):
    connection=connections[using]
    if not connection.in_atomic_block:raise RuntimeError('机构会话锁必须在数据库事务内使用')
    function='pg_advisory_xact_lock' if exclusive else 'pg_advisory_xact_lock_shared'
    with connection.cursor() as cursor:cursor.execute(f'SELECT {function}(%s)',[workspace_lock_key(context_id)])
