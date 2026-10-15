from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor,tenant_transaction
from .identity_store import probe_phone

def probe_login_phone(actor,phone):
    if actor.tenant_id:
        with tenant_transaction(actor.tenant_id):return probe_phone(actor,phone)
    return probe_phone(actor,phone)

class PhoneStatusView(APIView):
    def post(self,request):return Response(probe_login_phone(current_actor(request),request.data.get('phone')))
