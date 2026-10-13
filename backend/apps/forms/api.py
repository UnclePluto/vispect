from django.db.models import Q,OuterRef,Subquery
from .models import FormVersion
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.core.helpers import get_object
from apps.core.pagination import paginate
from apps.doctors.api import edit_revision
from .selectors import visible_forms
from .serializers import DefinitionSerializer,form_payload,version_payload
from .services import create_form,save_draft,publish_form,set_form_paused,delete_form,restore_form

class FormsView(APIView):
    def get(self,request):
        actor=current_actor(request);query=visible_forms(actor)
        # Filter on the title that this actor is authorized to see, never on private drafts.
        term=request.query_params.get('search','').lower()
        if term:
            if actor.role=='tenant_admin':query=query.filter(draft_definition__title__icontains=term)
            else:
                query=query.annotate(public_title=Subquery(FormVersion.objects.filter(form_id=OuterRef('pk')).order_by('-number').values('definition__title')[:1]))
                query=query.filter(Q(owner_id=actor.account_id,draft_definition__title__icontains=term)|(~Q(owner_id=actor.account_id)&Q(public_title__icontains=term)))
        return Response(paginate(query,request,lambda f:form_payload(f,actor)))
    def post(self,request):
        actor=current_actor(request);data=DefinitionSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(form_payload(create_form(actor,data.validated_data['definition']),actor),status=201)

class FormDetailView(APIView):
    def get(self,request,form_id):
        actor=current_actor(request);return Response(form_payload(get_object(visible_forms(actor),form_id),actor))
    def patch(self,request,form_id):
        actor=current_actor(request);data=DefinitionSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(form_payload(save_draft(actor,form_id,data.validated_data['definition'],edit_revision(request)),actor))
    def delete(self,request,form_id):
        actor=current_actor(request);return Response(form_payload(delete_form(actor,form_id,edit_revision(request)),actor))

class FormVersionsView(APIView):
    def get(self,request,form_id):
        form=get_object(visible_forms(current_actor(request)),form_id)
        return Response({'count':form.versions.count(),'results':[version_payload(v) for v in form.versions.all()]})

class FormPublishView(APIView):
    def post(self,request,form_id):return Response(version_payload(publish_form(current_actor(request),form_id,edit_revision(request),request.headers.get('Idempotency-Key',''))),status=201)

class FormStateView(APIView):
    action='pause'
    def post(self,request,form_id):
        actor=current_actor(request)
        form=restore_form(actor,form_id,edit_revision(request)) if self.action=='restore' else set_form_paused(actor,form_id,self.action=='pause',edit_revision(request))
        return Response(form_payload(form,actor))

class PublishedVersionOptionsView(APIView):
    def get(self,request):
        from apps.core.permissions import require_tenant
        actor=current_actor(request);require_tenant(actor)
        query=FormVersion.objects.filter(tenant_id=actor.tenant_id,form__deleted_at__isnull=True).select_related('form').order_by('form_id','-number')
        return Response(paginate(query,request,lambda v:{'id':str(v.id),'form_id':str(v.form_id),'title':v.definition['title'],'number':v.number,'paused':v.form.paused}))
