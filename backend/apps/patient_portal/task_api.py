from rest_framework.views import APIView
from rest_framework.response import Response
from .authentication import PatientSessionAuthentication
from .permissions import PatientPermission
from .auth_api import EntryTokenSerializer
from .tasks import resolve_patient_tasks,get_patient_task

class PatientAPIView(APIView):
    authentication_classes=[PatientSessionAuthentication]
    permission_classes=[PatientPermission]

class PatientTasksResolveView(PatientAPIView):
    def post(self,request):
        data=EntryTokenSerializer(data=request.data);data.is_valid(raise_exception=True)
        results=resolve_patient_tasks(request._request.patient_principal,data.validated_data['entry_token'])
        return Response({'count':len(results),'results':results})

class PatientTaskDetailView(PatientAPIView):
    def get(self,request,token,patient_id):
        return Response(get_patient_task(request._request.patient_principal,token,patient_id))
