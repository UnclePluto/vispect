from django.middleware.csrf import rotate_token
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.core.permissions import PrincipalPermission
from .session_context import authenticate_phone,start_login,auth_envelope

class PhoneLoginSerializer(serializers.Serializer):
    phone=serializers.CharField(max_length=40)
    password=serializers.CharField(trim_whitespace=False)
    def to_internal_value(self,data):
        unknown=set(data)-set(self.fields)
        if unknown:raise serializers.ValidationError({name:['不支持的登录字段'] for name in unknown})
        return super().to_internal_value(data)

class PhoneLoginView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        data=PhoneLoginSerializer(data=request.data);data.is_valid(raise_exception=True)
        identity=authenticate_phone(**data.validated_data)
        response=start_login(request._request,identity);rotate_token(request._request)
        return Response(response)

class WorkspacesView(APIView):
    permission_classes=[PrincipalPermission]
    def get(self,request):
        options=auth_envelope(request._request)['workspaces']
        return Response({'count':len(options),'results':options})
