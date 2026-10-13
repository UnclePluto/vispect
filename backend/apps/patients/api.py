from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from apps.core.context import current_actor
from apps.core.helpers import get_object
from apps.core.pagination import paginate
from apps.doctors.api import edit_revision
from .selectors import visible_patients
from .serializers import PatientWriteSerializer,patient_payload
from .services import create_patient,update_patient,delete_patient,restore_patient,assign_doctors

class PatientsView(APIView):
    def get(self,request):
        query=visible_patients(current_actor(request));term=request.query_params.get('search','')
        if term:query=query.filter(Q(name__icontains=term)|Q(code__icontains=term))
        if request.query_params.get('status'):query=query.filter(status=request.query_params['status'])
        if request.query_params.get('doctor_id'):
            doctor_id=serializers.UUIDField().run_validation(request.query_params['doctor_id'])
            query=query.filter(responsibilities__doctor_id=doctor_id)
        return Response(paginate(query.distinct(),request,patient_payload))
    def post(self,request):
        actor=current_actor(request);data=PatientWriteSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(patient_payload(create_patient(actor,data.validated_data)),status=201)

class PatientDetailView(APIView):
    def get(self,request,patient_id):return Response(patient_payload(get_object(visible_patients(current_actor(request)),patient_id)))
    def patch(self,request,patient_id):
        data=PatientWriteSerializer(data={k:v for k,v in request.data.items() if k!='expected_revision'},partial=True);data.is_valid(raise_exception=True)
        return Response(patient_payload(update_patient(current_actor(request),patient_id,data.validated_data,edit_revision(request))))
    def delete(self,request,patient_id):return Response(patient_payload(delete_patient(current_actor(request),patient_id,edit_revision(request))))

class PatientAssignView(APIView):
    def post(self,request,patient_id):
        ids=serializers.ListField(child=serializers.UUIDField(),allow_empty=False).run_validation(request.data.get('doctor_ids'))
        return Response(patient_payload(assign_doctors(current_actor(request),patient_id,ids,edit_revision(request))))

class PatientRestoreView(APIView):
    def post(self,request,patient_id):return Response(patient_payload(restore_patient(current_actor(request),patient_id,edit_revision(request))))
