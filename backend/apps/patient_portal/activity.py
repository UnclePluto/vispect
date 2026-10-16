from .models import PatientActivity


def record_patient_activity(principal,action,object_id=None,metadata=None):
    safe={k:v for k,v in (metadata or {}).items() if not any(word in k.lower() for word in ['password','token','secret','credential'])}
    return PatientActivity.objects.create(tenant_id=principal.tenant_id,identity_id=principal.identity_id,action=action,object_id=object_id,metadata=safe)
