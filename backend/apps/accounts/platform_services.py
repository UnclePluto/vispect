from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.core.permissions import require_role
from apps.core.helpers import ensure_revision,get_object
from apps.core.errors import ApiError
from apps.core.audit import audit
from .models import LoginIdentity,LoginSessionContext
from .phone import normalize_phone

def global_payload(identity):
    return {'id':str(identity.id),'phone':identity.phone,'name':identity.name,'enabled':identity.is_active,'must_change_password':identity.must_change_password,'revision':identity.revision}

def find_global_account(actor,phone):
    require_role(actor,'platform_admin');phone=normalize_phone(phone)
    return [global_payload(i) for i in LoginIdentity.objects.using('control').filter(phone=phone)]

def update_global_account(actor,identity_id,data,*,reset=False):
    require_role(actor,'platform_admin')
    with transaction.atomic(using='control'):
        identity=get_object(LoginIdentity.objects.using('control'),identity_id,True);ensure_revision(identity,data['expected_revision'])
        if reset:
            try:validate_password(data['new_password'],identity)
            except ValidationError as exc:raise ApiError('validation_error','密码不符合要求',{'new_password':list(exc.messages)},400) from exc
            identity.set_password(data['new_password']);identity.must_change_password=True
        else:identity.is_active=data['enabled']
        identity.revision+=1;identity.save(using='control')
        if reset or not identity.is_active:LoginSessionContext.objects.using('control').filter(identity=identity).update(revoked=True)
        audit(actor,'reset_global_password' if reset else 'set_global_enabled','login_identity',identity.id,{'phone':identity.phone,'enabled':identity.is_active})
        return global_payload(identity)
