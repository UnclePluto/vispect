from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.crypto import constant_time_compare
from apps.core.errors import ApiError
from .models import Account

def check_credentials(username,password,alias='default',platform=False):
    accounts=Account.objects.using(alias).filter(username=username,is_active=True)
    accounts=accounts.filter(role='platform_admin',tenant__isnull=True) if platform else accounts.exclude(role='platform_admin')
    account=accounts.first()
    if not account or not account.check_password(password):
        raise ApiError('credentials_invalid','租户、用户名或密码不正确',status=401)
    return account

def start_session(request,account):
    request.session.cycle_key()
    request.session['identity']={'account_id':str(account.id),'tenant_id':str(account.tenant_id) if account.tenant_id else None,'auth_hash':account.get_session_auth_hash()}

def change_password(request,old_password,new_password):
    source=request._request.account
    alias='control' if source.role=='platform_admin' else 'default'
    account=Account.objects.using(alias).select_for_update().filter(id=source.id,is_active=True).first()
    identity=request.session.get('identity',{})
    if not account or not constant_time_compare(account.get_session_auth_hash(),identity.get('auth_hash','')):
        raise ApiError('session_unavailable','会话已失效，请重新登录',status=401)
    if not account.check_password(old_password):
        raise ApiError('old_password_invalid','原密码不正确',status=400)
    if new_password == old_password:
        raise ApiError('password_unchanged','新密码不能与原密码相同',{'new_password':['请设置不同的新密码']},400)
    try:validate_password(new_password,account)
    except ValidationError as exc:
        raise ApiError('validation_error','新密码不符合要求',{'new_password':list(exc.messages)},400)
    account.set_password(new_password)
    account.must_change_password=False
    account.revision+=1
    account.save(using=alias,update_fields=['password','must_change_password','revision'])
    start_session(request,account)
    return account
