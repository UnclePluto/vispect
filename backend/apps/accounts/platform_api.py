from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.core.permissions import require_role
from .platform_services import find_global_account,update_global_account

class GlobalAccountsView(APIView):
    def get(self,request):
        actor=current_actor(request);require_role(actor,'platform_admin')
        results=find_global_account(actor,request.query_params.get('phone'));return Response({'count':len(results),'results':results})

class GlobalEnabledSerializer(serializers.Serializer):
    enabled=serializers.BooleanField()
    expected_revision=serializers.IntegerField(min_value=1)
class GlobalResetSerializer(serializers.Serializer):
    new_password=serializers.CharField(trim_whitespace=False,write_only=True)
    expected_revision=serializers.IntegerField(min_value=1)
class GlobalAccountActionView(APIView):
    reset=False
    def post(self,request,identity_id):
        actor=current_actor(request);require_role(actor,'platform_admin')
        serializer=(GlobalResetSerializer if self.reset else GlobalEnabledSerializer)(data=request.data);serializer.is_valid(raise_exception=True)
        return Response(update_global_account(actor,identity_id,serializer.validated_data,reset=self.reset))
