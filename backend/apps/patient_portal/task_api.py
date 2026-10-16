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

from .answers import save_patient_answer,submit_patient_answer
from .serializers import PatientAnswerWriteSerializer
from apps.followups.serializers import answer_payload

class PatientTaskAnswersView(PatientAPIView):
    def post(self,request,token,patient_id):
        data=PatientAnswerWriteSerializer(data=request.data);data.is_valid(raise_exception=True);values=data.validated_data
        principal=request._request.patient_principal
        args=(principal,token,patient_id,values['answers'],values['expected_revision'])
        answer=save_patient_answer(*args) if values['action']=='draft' else submit_patient_answer(*args,request.headers.get('Idempotency-Key',''))
        return Response(answer_payload(answer))
