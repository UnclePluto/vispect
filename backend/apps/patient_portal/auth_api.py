from django.conf import settings
from django.middleware.csrf import get_token,rotate_token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from apps.core.context import tenant_transaction
from .authentication import PatientSessionAuthentication
from .serializers import StrictSerializer
from .sessions import authenticate_patient,start_patient_login,patient_transaction,auth_envelope,change_patient_password,logout_patient,check_entry
from .scope_store import resolve_entry_scope

class EntryTokenSerializer(StrictSerializer):
    entry_token=serializers.CharField(max_length=128)

class PatientLoginSerializer(EntryTokenSerializer):
    phone=serializers.CharField(max_length=40)
    password=serializers.CharField(trim_whitespace=False,max_length=1024)

class PatientPasswordSerializer(StrictSerializer):
    old_password=serializers.CharField(trim_whitespace=False,max_length=1024)
    new_password=serializers.CharField(trim_whitespace=False,max_length=1024)

class PatientAuthView(APIView):
    authentication_classes=[PatientSessionAuthentication]
    permission_classes=[AllowAny]
    def credential_response(self,request,payload):
        response=Response(payload)
        raw=getattr(request._request,'patient_cookie_value',None)
        if raw:response.set_cookie(settings.PATIENT_SESSION_COOKIE_NAME,raw,max_age=settings.SESSION_COOKIE_AGE,httponly=True,secure=settings.SESSION_COOKIE_SECURE,samesite='Lax',path='/api/patient/')
        return response

class PatientCsrfView(PatientAuthView):
    def get(self,request):return Response({'csrf_token':get_token(request._request)})

class PatientEntryResolveView(PatientAuthView):
    def post(self,request):
        data=EntryTokenSerializer(data=request.data);data.is_valid(raise_exception=True)
        tenant_id,entry_id=resolve_entry_scope(data.validated_data['entry_token'])
        with tenant_transaction(tenant_id):check_entry(entry_id)
        return Response({'available':True})

class PatientLoginView(PatientAuthView):
    def post(self,request):
        data=PatientLoginSerializer(data=request.data);data.is_valid(raise_exception=True)
        values=data.validated_data;identity=authenticate_patient(**values)
        request._request.patient_entry_token=values['entry_token']
        payload=start_patient_login(request._request,identity)
        # Keep the shared CSRF cookie stable: rotating it here would invalidate
        # an in-flight staff tab even though the patient credential is separate.
        return self.credential_response(request,payload)

class PatientMeView(PatientAuthView):
    def get(self,request):
        with patient_transaction(request._request,require_changed_password=False,check_token=False):
            return Response(auth_envelope(request._request.patient_identity,request._request.patient_session))

class PatientChangePasswordView(PatientAuthView):
    def post(self,request):
        data=PatientPasswordSerializer(data=request.data);data.is_valid(raise_exception=True)
        return self.credential_response(request,change_patient_password(request._request,**data.validated_data))

class PatientLogoutView(PatientAuthView):
    def post(self,request):
        logout_patient(request._request)
        response=Response({'ok':True});response.delete_cookie(settings.PATIENT_SESSION_COOKIE_NAME,path='/api/patient/',samesite='Lax');return response
