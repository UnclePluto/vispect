from django.db.models import Q,Exists,OuterRef
from apps.core.permissions import require_tenant
from .models import Form,FormVersion

def editable_forms(actor,include_deleted=False):
    require_tenant(actor);query=Form.objects.filter(tenant_id=actor.tenant_id)
    if not include_deleted:query=query.filter(deleted_at__isnull=True)
    if actor.role!='tenant_admin':query=query.filter(owner_id=actor.account_id)
    return query

def visible_forms(actor):
    require_tenant(actor);query=Form.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=True)
    if actor.role!='tenant_admin':query=query.annotate(published=Exists(FormVersion.objects.filter(form_id=OuterRef('pk')))).filter(Q(owner_id=actor.account_id)|Q(published=True))
    return query
