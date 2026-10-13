from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from apps.core.context import current_actor
from apps.core.helpers import get_object
from apps.core.pagination import paginate
from apps.doctors.api import edit_revision
from apps.studies.selectors import require_study_member
from .enrollments import add_subject,confirm_enrollment,transfer_followup
from .selectors import visible_enrollments,visible_visits
from .serializers import enrollment_payload,visit_payload
class AddSubjectSerializer(serializers.Serializer):
    patient_id=serializers.UUIDField()
    doctor_id=serializers.UUIDField()
    observation_code=serializers.CharField(max_length=100)
    def validate_observation_code(self,value):
        if not isinstance(self.initial_data.get('observation_code'),str):raise serializers.ValidationError('编号须为字符串')
        return value
class ConfirmSerializer(serializers.Serializer):
    enrollment_code=serializers.CharField(max_length=100)
    enrolled_on=serializers.DateField()
    def validate_enrollment_code(self,value):
        if not isinstance(self.initial_data.get('enrollment_code'),str):raise serializers.ValidationError('编号须为字符串')
        return value
class StudySubjectsView(APIView):
    def get(self,request,study_id):
        actor=current_actor(request);require_study_member(actor,study_id);query=visible_enrollments(actor).filter(study_id=study_id).select_related('study','patient','doctor')
        if request.query_params.get('state'):query=query.filter(state=request.query_params['state'])
        if request.query_params.get('search'):
            from django.db.models import Q
            term=request.query_params['search'];query=query.filter(Q(patient__name__icontains=term)|Q(patient__code__icontains=term)|Q(observation_code__icontains=term)|Q(enrollment_code__icontains=term))
        return Response(paginate(query,request,enrollment_payload))
    def post(self,request,study_id):
        data=AddSubjectSerializer(data=request.data);data.is_valid(raise_exception=True)
        e=add_subject(current_actor(request),study_id,key=request.headers.get('Idempotency-Key',''),**data.validated_data)
        return Response(enrollment_payload(e),status=201)
class EnrollmentDetailView(APIView):
    def get(self,request,enrollment_id):
        actor=current_actor(request);e=get_object(visible_enrollments(actor),enrollment_id);data=enrollment_payload(e)
        data['visits']=[visit_payload(v) for v in visible_visits(actor).filter(enrollment=e).select_related('enrollment__study','enrollment__patient','enrollment__doctor','stage').order_by('stage__position')]
        return Response(data)
class EnrollmentConfirmView(APIView):
    def post(self,request,enrollment_id):
        data=ConfirmSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(enrollment_payload(confirm_enrollment(current_actor(request),enrollment_id,key=request.headers.get('Idempotency-Key',''),**data.validated_data)))
class EnrollmentTransferView(APIView):
    def post(self,request,enrollment_id):
        doctor_id=serializers.UUIDField().run_validation(request.data.get('doctor_id'))
        return Response(enrollment_payload(transfer_followup(current_actor(request),enrollment_id,doctor_id,edit_revision(request))))
class VisitsView(APIView):
    def get(self,request):
        query=visible_visits(current_actor(request)).select_related('enrollment__study','enrollment__patient','enrollment__doctor','stage')
        for param,field in [('study_id','study_id'),('doctor_id','enrollment__doctor_id'),('enrollment_id','enrollment_id')]:
            if request.query_params.get(param):query=query.filter(**{field:serializers.UUIDField().run_validation(request.query_params[param])})
        for param,lookup in [('date_from','planned_on__gte'),('date_to','planned_on__lte')]:
            if request.query_params.get(param):query=query.filter(**{lookup:serializers.DateField().run_validation(request.query_params[param])})
        if request.query_params.get('status'):query=query.filter(status=request.query_params['status'])
        return Response(paginate(query,request,visit_payload))
class VisitDetailView(APIView):
    def get(self,request,visit_id):return Response(visit_payload(get_object(visible_visits(current_actor(request)),visit_id),True))
