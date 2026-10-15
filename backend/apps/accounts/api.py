from django.middleware.csrf import get_token,rotate_token
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from apps.core.context import tenant_transaction,current_actor
from apps.core.errors import ApiError
from apps.tenants.lookup import lookup_tenant
from .serializers import LoginSerializer,ChangePasswordSerializer,identity_payload
from .services import check_credentials,start_session,change_password

class CsrfView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        return Response({'csrf_token':get_token(request._request)})

class TenantLoginView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        data=LoginSerializer(data=request.data);data.is_valid(raise_exception=True)
        tenant=lookup_tenant(data.validated_data.get('tenant'))
        if not tenant:raise ApiError('credentials_invalid','租户、用户名或密码不正确',status=401)
        with tenant_transaction(tenant.id):
            account=check_credentials(data.validated_data['username'],data.validated_data['password'])
            start_session(request,account)
            rotate_token(request._request)
            return Response(identity_payload(account))

class PlatformLoginView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        data=LoginSerializer(data=request.data);data.is_valid(raise_exception=True)
        with transaction.atomic(using='control'):
            account=check_credentials(data.validated_data['username'],data.validated_data['password'],'control',True)
            start_session(request,account)
            rotate_token(request._request)
            return Response(identity_payload(account))

class MeView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):
        if getattr(request,'principal',None):
            from .session_context import auth_envelope
            return Response(auth_envelope(request._request))
        current_actor(request)
        return Response(identity_payload(request._request.account))

class LogoutView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        if getattr(request,'principal',None):
            from .models import LoginSessionContext
            LoginSessionContext.objects.using('control').filter(id=request.principal.context_id).update(revoked=True)
        request.session.flush()
        return Response({'success':True})

class ChangePasswordView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        data=ChangePasswordSerializer(data=request.data);data.is_valid(raise_exception=True)
        if getattr(request,'principal',None):
            from .session_context import change_identity_password
            return Response(change_identity_password(request._request,**data.validated_data))
        current_actor(request)
        account=change_password(request,**data.validated_data)
        return Response(identity_payload(account))
