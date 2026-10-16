from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from .access import open_patient_access,access_payload
from .serializers import OpenAccessSerializer

class PatientAccessView(APIView):
    def post(self,request,patient_id):
        data=OpenAccessSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(access_payload(open_patient_access(current_actor(request),patient_id,**data.validated_data)))
