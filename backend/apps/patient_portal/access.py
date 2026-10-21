import hashlib
from django.db import connection
from apps.accounts.phone import normalize_phone
from apps.core.audit import audit
from apps.core.errors import ApiError
from apps.core.helpers import get_object,ensure_revision
from apps.patients.selectors import visible_patients
from apps.tenants.quota import mutate_with_quota
from .models import PatientLoginIdentity,PatientAccess


def bind_patient_login(actor,patient,phone):
    phone=normalize_phone(phone)
    lock=int.from_bytes(hashlib.sha256(f'vispect.patient.phone:{actor.tenant_id}:{phone}'.encode()).digest()[:8],'big',signed=True)
    with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_xact_lock(%s)',[lock])
    existing=PatientAccess.objects.select_related('identity').filter(patient_id=patient.id).first()
    if existing:
        if existing.identity.phone!=phone:raise ApiError('patient_access_exists','患者已开通填写账号，本入口不支持换绑',status=409)
        return existing
    identity=PatientLoginIdentity.objects.filter(tenant_id=actor.tenant_id,phone=phone).first()
    if identity is None:
        identity=PatientLoginIdentity(tenant_id=actor.tenant_id,phone=phone)
        identity.set_password('888888');identity.save()
    access=PatientAccess.objects.create(tenant_id=actor.tenant_id,patient_id=patient.id,identity_id=identity.id)
    audit(actor,'open_patient_access','patient',patient.id,{'identity_id':str(identity.id)})
    return access


def open_patient_access(actor,patient_id,phone,expected_revision):
    def mutation():
        patient=get_object(visible_patients(actor),patient_id,True);ensure_revision(patient,expected_revision)
        return bind_patient_login(actor,patient,phone)
    return mutate_with_quota(actor,'patients',mutation,delta=0)


def access_payload(access):
    identity=access.identity
    return {'id':str(access.id),'patient_id':str(access.patient_id),'login_phone':identity.phone,'must_change_password':identity.must_change_password,'enabled':identity.is_active,'revision':access.revision}
