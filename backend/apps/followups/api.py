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

from .answers import save_answer_draft,submit_answer,revise_answer
from .transitions import complete_visit,stop_followup
from .selectors import visible_answers
from .serializers import answer_payload
class AnswerWriteSerializer(serializers.Serializer):
    binding_id=serializers.UUIDField()
    answers=serializers.JSONField()
    action=serializers.ChoiceField(choices=['draft','submit'])
    expected_revision=serializers.IntegerField(min_value=0)
class VisitAnswersView(APIView):
    def get(self,request,visit_id):
        actor=current_actor(request);get_object(visible_visits(actor),visit_id)
        return Response({'results':[answer_payload(a) for a in visible_answers(actor).filter(visit_id=visit_id).select_related('recorded_by')]})
    def post(self,request,visit_id):
        actor=current_actor(request);data=AnswerWriteSerializer(data=request.data);data.is_valid(raise_exception=True);values=data.validated_data
        if values['action']=='draft':
            if 'expected_revision' not in values:raise serializers.ValidationError({'expected_revision':['请提供答案修订号']})
            answer=save_answer_draft(actor,visit_id,values['binding_id'],values['answers'],values['expected_revision'])
        else:answer=submit_answer(actor,visit_id,values['binding_id'],values['answers'],request.headers.get('Idempotency-Key',''),values['expected_revision'])
        return Response(answer_payload(answer))
class AnswerDetailView(APIView):
    def get(self,request,answer_id):return Response(answer_payload(get_object(visible_answers(current_actor(request)),answer_id)))
class AnswerReviseView(APIView):
    def post(self,request,answer_id):
        return Response(answer_payload(revise_answer(current_actor(request),answer_id,request.data.get('answers'),request.data.get('reason'),edit_revision(request))))
class VisitCompleteView(APIView):
    def post(self,request,visit_id):return Response(visit_payload(complete_visit(current_actor(request),visit_id,request.headers.get('Idempotency-Key',''))))
class EnrollmentStopView(APIView):
    def post(self,request,enrollment_id):return Response(enrollment_payload(stop_followup(current_actor(request),enrollment_id,request.data.get('stop_type'),request.data.get('reason'),request.headers.get('Idempotency-Key',''))))

from django.http import HttpResponse
from .exports import export_answers
from .history import visible_answer_revisions,revision_payload
class StudyExportView(APIView):
    def get(self,request,study_id):
        response=HttpResponse(export_answers(current_actor(request),study_id=study_id),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition']='attachment; filename="study-answers.xlsx"';response['Cache-Control']='no-store';return response
class AnswerExportView(APIView):
    def get(self,request,answer_id):
        response=HttpResponse(export_answers(current_actor(request),answer_id=answer_id),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition']='attachment; filename="answer.xlsx"';response['Cache-Control']='no-store';return response
class AnswerRevisionsView(APIView):
    def get(self,request,answer_id):return Response(paginate(visible_answer_revisions(current_actor(request),answer_id),request,revision_payload))

class StudyAnswersView(APIView):
    def get(self,request,study_id):
        actor=current_actor(request);require_study_member(actor,study_id)
        query=visible_answers(actor).filter(visit__study_id=study_id).select_related('recorded_by','form_version','visit__stage','visit__enrollment__patient')
        def payload(a):return {**answer_payload(a),'patient_name':a.visit.enrollment.patient.name,'patient_code':a.visit.enrollment.patient.code,'stage_name':a.visit.stage.name,'form_title':a.form_version.definition['title'],'version_number':a.form_version.number}
        return Response(paginate(query,request,payload))
