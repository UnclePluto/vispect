from django.db import connections
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.core.permissions import require_role
from apps.core.helpers import get_object
from apps.core.errors import ApiError
from apps.core.pagination import paginate
from .models import Tenant
from .serializers import TenantWriteSerializer,AdministratorSerializer,tenant_payload
from .services import create_tenant,update_tenant,configure_administrator

class TenantsView(APIView):
    def get(self,request):
        require_role(current_actor(request),'platform_admin')
        query=Tenant.objects.using('control').select_related('quota').order_by('-created_at','id')
        if request.query_params.get('search'):query=query.filter(name__icontains=request.query_params['search'])
        return Response(paginate(query,request,tenant_payload))
    def post(self,request):
        actor=current_actor(request);require_role(actor,'platform_admin')
        data=TenantWriteSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(tenant_payload(create_tenant(actor,data.validated_data)),status=201)

class TenantDetailView(APIView):
    def get(self,request,tenant_id):
        require_role(current_actor(request),'platform_admin')
        return Response(tenant_payload(get_object(Tenant.objects.using('control').select_related('quota'),tenant_id)))
    def patch(self,request,tenant_id):
        actor=current_actor(request);require_role(actor,'platform_admin')
        expected=request.data.get('expected_revision')
        if isinstance(expected,bool) or not isinstance(expected,int):raise ApiError('validation_error','请提供记录修订号',status=400)
        data=TenantWriteSerializer(data={k:v for k,v in request.data.items() if k!='expected_revision'},partial=True);data.is_valid(raise_exception=True)
        return Response(tenant_payload(update_tenant(actor,tenant_id,data.validated_data,expected)))

class AdministratorView(APIView):
    def get(self,request,tenant_id):
        from apps.accounts.models import Account
        require_role(current_actor(request),'platform_admin')
        account=Account.objects.using('control').filter(tenant_id=tenant_id,role='tenant_admin').order_by('created_at').first()
        if not account:raise ApiError('object_unavailable','管理员账号不可用',status=404)
        return Response({'id':str(account.id),'username':account.username,'name':account.name,'enabled':account.is_active,'revision':account.revision})
    def patch(self,request,tenant_id):
        actor=current_actor(request);require_role(actor,'platform_admin')
        data=AdministratorSerializer(data=request.data);data.is_valid(raise_exception=True)
        account=configure_administrator(actor,tenant_id,data.validated_data)
        return Response({'id':str(account.id),'username':account.username,'name':account.name,'enabled':account.is_active,'revision':account.revision})

class PlatformUsageView(APIView):
    def get(self,request):
        require_role(current_actor(request),'platform_admin')
        with connections['control'].cursor() as cur:
            cur.execute('SELECT * FROM vispect_platform_usage() ORDER BY tenant_id')
            rows=cur.fetchall()
        return Response({'count':len(rows),'results':[{'tenant_id':str(r[0]),'tenant_name':r[1],'doctors':r[2],'patients':r[3],'studies':r[4]} for r in rows]})
