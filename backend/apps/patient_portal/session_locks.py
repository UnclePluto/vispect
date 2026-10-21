import hashlib
from uuid import UUID
from django.db import connection


def lock_patient_identity(identity_id,*,exclusive=False):
    if not connection.in_atomic_block:raise RuntimeError('患者会话锁必须位于事务内')
    key=int.from_bytes(hashlib.sha256(b'vispect.patient.identity:'+UUID(str(identity_id)).bytes).digest()[:8],'big',signed=True)
    function='pg_advisory_xact_lock' if exclusive else 'pg_advisory_xact_lock_shared'
    with connection.cursor() as cursor:cursor.execute(f'SELECT {function}(%s)',[key])
