from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from apps.core.context import current_actor
from apps.core.helpers import get_object
from apps.core.pagination import paginate
from apps.doctors.api import edit_revision
from .selectors import visible_studies
from .serializers import StudyWriteSerializer,study_payload
from .services import create_study,update_study,set_study_state,delete_study,restore_study,set_study_members,save_protocol
class StudiesView(APIView):
    def get(self,request):
        actor=current_actor(request);query=visible_studies(actor).select_related('owner');term=request.query_params.get('search','')
        if term:query=query.filter(Q(name__icontains=term)|Q(code__icontains=term))
        if request.query_params.get('state'):query=query.filter(state=request.query_params['state'])
        return Response(paginate(query,request,lambda s:study_payload(s,actor)))
    def post(self,request):
        actor=current_actor(request);data=StudyWriteSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(study_payload(create_study(actor,data.validated_data),actor,True),status=201)
class StudyDetailView(APIView):
    def get(self,request,study_id):
        actor=current_actor(request);return Response(study_payload(get_object(visible_studies(actor),study_id),actor,True))
    def patch(self,request,study_id):
        actor=current_actor(request);data=StudyWriteSerializer(data={k:v for k,v in request.data.items() if k!='expected_revision'},partial=True);data.is_valid(raise_exception=True)
        return Response(study_payload(update_study(actor,study_id,data.validated_data,edit_revision(request)),actor,True))
    def delete(self,request,study_id):
        actor=current_actor(request);return Response(study_payload(delete_study(actor,study_id,edit_revision(request)),actor,True))
class StudyMembersView(APIView):
    def post(self,request,study_id):
        ids=serializers.ListField(child=serializers.UUIDField()).run_validation(request.data.get('doctor_ids'));actor=current_actor(request)
        return Response(study_payload(set_study_members(actor,study_id,ids,edit_revision(request)),actor,True))
class StudyProtocolView(APIView):
    def post(self,request,study_id):
        actor=current_actor(request);return Response(study_payload(save_protocol(actor,study_id,request.data.get('stages'),edit_revision(request)),actor,True))
class StudyStateView(APIView):
    state='active'
    def post(self,request,study_id):
        actor=current_actor(request);s=restore_study(actor,study_id,edit_revision(request)) if self.state=='restore' else set_study_state(actor,study_id,self.state,edit_revision(request))
        return Response(study_payload(s,actor,True))
