from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import ChangePasswordSerializer
from .principal import get_principal
from .session_context import auth_envelope,change_identity_password

class CsrfView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):return Response({'csrf_token':get_token(request._request)})

class MeView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):return Response(auth_envelope(request._request))

class LogoutView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        if getattr(request,'principal',None):
            from .models import LoginSessionContext
            LoginSessionContext.objects.using('control').filter(id=request.principal.context_id).update(revoked=True)
        request.session.flush();return Response({'success':True})

class ChangePasswordView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        get_principal(request._request)
        data=ChangePasswordSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(change_identity_password(request._request,**data.validated_data))
