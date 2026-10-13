from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from .context import current_actor
from .permissions import require_role,require_tenant
from .pagination import paginate
from .models import AuditEvent

def event_payload(event):
    return {'id':str(event.id),'tenant_id':str(event.tenant_id) if event.tenant_id else None,'actor_id':str(event.actor_id),'actor_name':event.actor.name,'action':event.action,'object_type':event.object_type,'object_id':str(event.object_id),'changes':event.changes,'created_at':event.created_at.isoformat()}
class AuditView(APIView):
    platform=False
    def get(self,request):
        actor=current_actor(request)
        if self.platform:require_role(actor,'platform_admin');query=AuditEvent.objects.using('control').filter(tenant_id=None)
        else:require_tenant(actor);require_role(actor,'tenant_admin');query=AuditEvent.objects.filter(tenant_id=actor.tenant_id)
        query=query.select_related('actor')
        for key in ['action','object_type']:
            if request.query_params.get(key):query=query.filter(**{key:request.query_params[key]})
        if request.query_params.get('object_id'):query=query.filter(object_id=serializers.UUIDField().run_validation(request.query_params['object_id']))
        return Response(paginate(query,request,event_payload))
