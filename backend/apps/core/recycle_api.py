from django.db.models import F,Value,CharField
from django.db.models.fields.json import KeyTextTransform
from rest_framework.views import APIView
from rest_framework.response import Response
from .context import current_actor
from .permissions import require_tenant,require_role
from .pagination import paginate
from .errors import ApiError
from apps.doctors.models import Doctor
from apps.patients.models import Patient
from apps.studies.models import Study
from apps.forms.models import Form
class RecycleView(APIView):
    def get(self,request):
        actor=current_actor(request);require_tenant(actor);require_role(actor,'tenant_admin')
        selected=request.query_params.get('resource');models={'doctor':Doctor,'patient':Patient,'study':Study,'form':Form}
        if selected and selected not in models:raise ApiError('validation_error','回收资源类型无效',status=400)
        queries=[]
        for resource,model in models.items():
            if selected and selected!=resource:continue
            name=KeyTextTransform('title','draft_definition') if resource=='form' else F('name')
            queries.append(model.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=False).order_by().annotate(resource=Value(resource,output_field=CharField()),display_name=name).values('id','revision','deleted_at','resource','display_name'))
        query=queries[0].union(*queries[1:],all=True).order_by('-deleted_at','id')
        return Response(paginate(query,request,lambda r:{'id':str(r['id']),'revision':r['revision'],'deleted_at':r['deleted_at'].isoformat(),'resource':r['resource'],'name':r['display_name']}))
