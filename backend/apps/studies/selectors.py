from apps.core.permissions import require_tenant
from apps.core.helpers import get_object
from .models import Study

def visible_studies(actor,include_deleted=False):
    require_tenant(actor);query=Study.objects.filter(tenant_id=actor.tenant_id)
    if not include_deleted:query=query.filter(deleted_at__isnull=True)
    if actor.role=='doctor':query=query.filter(memberships__doctor_id=actor.doctor_id)
    return query

def editable_studies(actor,include_deleted=False):
    query=visible_studies(actor,include_deleted)
    if actor.role=='doctor':query=query.filter(owner_id=actor.doctor_id)
    return query

def require_study_member(actor,study_id):return get_object(visible_studies(actor),study_id)
