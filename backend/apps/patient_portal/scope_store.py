import hashlib
from django.db import connection
from apps.core.errors import ApiError


def digest_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def resolve_entry_scope(token: str):
    if not isinstance(token,str) or not token or len(token)>128:
        raise ApiError('entry_unavailable','填写链接已失效，请联系医生',status=404)
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM vispect_patient_entry_scope(%s)',[digest_token(token)])
        row=cursor.fetchone()
    if row is None:raise ApiError('entry_unavailable','填写链接已失效，请联系医生',status=404)
    return tuple(row)


def resolve_session_scope(raw_cookie: str):
    if not raw_cookie or len(raw_cookie)>128:return None
    with connection.cursor() as cursor:
        cursor.execute('SELECT * FROM vispect_patient_session_scope(%s)',[digest_token(raw_cookie)])
        row=cursor.fetchone()
    return tuple(row) if row else None


def revoke_session_digest(digest: str):
    with connection.cursor() as cursor:
        cursor.execute('SELECT vispect_revoke_patient_session(%s)',[digest])
        return cursor.fetchone()[0]
