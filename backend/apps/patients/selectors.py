from apps.core.permissions import require_tenant
from .models import Patient

def visible_patients(actor,include_deleted=False):
    require_tenant(actor)
    query=Patient.objects.filter(tenant_id=actor.tenant_id)
    if not include_deleted:query=query.filter(deleted_at__isnull=True)
    if actor.role=='doctor':query=query.filter(responsibilities__doctor_id=actor.doctor_id)
    return query.prefetch_related('responsibilities__doctor')
