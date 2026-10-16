from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.core.errors import ApiError
from .access import open_patient_access,access_payload
from .serializers import OpenAccessSerializer

class PatientAccessView(APIView):
    def post(self,request,patient_id):
        data=OpenAccessSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(access_payload(open_patient_access(current_actor(request),patient_id,**data.validated_data)))

from apps.core.helpers import get_object
from apps.core.pagination import paginate
from apps.doctors.api import edit_revision
from apps.studies.models import FormBinding
from apps.studies.selectors import visible_studies
from .entries import entry_candidates,entry_payload,creation_block,get_or_create_entry,change_entry
from .models import PatientFormEntry

class PatientEntryOptionsView(APIView):
    def get(self,request,form_id):
        actor=current_actor(request)
        def payload(binding):
            entry=PatientFormEntry.objects.filter(binding_id=binding.id).first()
            return {'binding_id':str(binding.id),'study_id':str(binding.stage.study_id),'study_name':binding.stage.study.name,'stage_name':binding.stage.name,'form_title':binding.form_version.definition['title'],'version_number':binding.form_version.number,'entry':entry_payload(entry) if entry else None,'create_block_reason':creation_block(binding)}
        return Response(paginate(entry_candidates(actor,form_id).order_by('stage__study_id','stage__position','id'),request,payload))

class PatientBindingEntryView(APIView):
    def get(self,request,binding_id):
        actor=current_actor(request)
        binding=get_object(FormBinding.objects.filter(tenant_id=actor.tenant_id,respondent='patient',stage__study_id__in=visible_studies(actor).values('id')).exclude(stage__kind='screening'),binding_id)
        entry=PatientFormEntry.objects.filter(binding_id=binding.id).first()
        return Response({'entry':entry_payload(entry) if entry else None})
    def post(self,request,binding_id):
        if request.data:raise ApiError('forbidden_fields','此操作不接受附加字段',status=400)
        return Response(entry_payload(get_or_create_entry(current_actor(request),binding_id)))

class PatientEntryActionView(APIView):
    action='disable'
    def post(self,request,entry_id):
        return Response(entry_payload(change_entry(current_actor(request),entry_id,self.action,edit_revision(request))))
