from apps.core.permissions import require_tenant
from .models import Enrollment,VisitInstance
ACTIVE_STATES=['screening','awaiting_enrollment','following']
def visible_enrollments(actor):
    require_tenant(actor)
    query=Enrollment.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=True,study__deleted_at__isnull=True,patient__deleted_at__isnull=True)
    if actor.role=='doctor':query=query.filter(study__memberships__doctor_id=actor.doctor_id,patient__responsibilities__doctor_id=actor.doctor_id)
    return query

def visible_visits(actor):
    require_tenant(actor)
    return VisitInstance.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=True,enrollment_id__in=visible_enrollments(actor).values('id'))
