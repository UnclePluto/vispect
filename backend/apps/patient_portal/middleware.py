from django.http import JsonResponse
from apps.core.errors import ApiError
from .sessions import patient_transaction

class PatientPortalMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if not request.path.startswith('/api/patient/'):return self.get_response(request)
        request.actor=None
        try:
            if request.path.startswith('/api/patient/auth/') or request.path in ['/api/patient/csrf/','/api/patient/entry/resolve/']:
                response=self.get_response(request)
            else:
                with patient_transaction(request):response=self.get_response(request)
        except ApiError as exc:
            response=JsonResponse({'code':exc.code,'message':exc.message,'fields':exc.fields},status=exc.status)
        response['Cache-Control']='no-store'
        return response
