from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.core.helpers import get_object
from apps.core.permissions import require_tenant
from apps.core.errors import ApiError
from apps.core.pagination import paginate
from .serializers import DoctorWriteSerializer,doctor_payload
from .services import visible_doctors,create_doctor,update_doctor,delete_doctor,restore_doctor,set_doctor_enabled
from .models import Doctor

def edit_revision(request):
    revision=request.data.get('expected_revision')
    if not isinstance(revision,int) or isinstance(revision,bool):raise ApiError('validation_error','请提供记录修订号',status=400)
    return revision

class DoctorsView(APIView):
    def get(self,request):
        actor=current_actor(request);query=visible_doctors(actor)
        if request.query_params.get('search'):
            term=request.query_params['search']
            from django.db.models.expressions import RawSQL
            query=query.annotate(login_phone=RawSQL('vispect_member_phone(%s,account_id)',[actor.account_id])).filter(Q(name__icontains=term)|Q(login_phone__icontains=term))
        status=request.query_params.get('enabled')
        if status is not None:
            if status not in ['true','false']:raise ApiError('validation_error','状态筛选参数不正确',status=400)
            query=query.filter(account__is_active=status=='true')
        return Response(paginate(query,request,lambda d:doctor_payload(d,actor)))
    def post(self,request):
        actor=current_actor(request);require_tenant(actor)
        data=DoctorWriteSerializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(doctor_payload(create_doctor(actor,data.validated_data),actor),status=201)

class DoctorDetailView(APIView):
    def get(self,request,doctor_id):
        return Response(doctor_payload(get_object(visible_doctors(current_actor(request)),doctor_id),current_actor(request)))
    def patch(self,request,doctor_id):
        actor=current_actor(request);require_tenant(actor)
        revision=edit_revision(request)
        data=DoctorWriteSerializer(data={k:v for k,v in request.data.items() if k!='expected_revision'},partial=True);data.is_valid(raise_exception=True)
        return Response(doctor_payload(update_doctor(actor,doctor_id,data.validated_data,revision),actor))
    def delete(self,request,doctor_id):
        return Response(doctor_payload(delete_doctor(current_actor(request),doctor_id,edit_revision(request)),current_actor(request)))

class DoctorRestoreView(APIView):
    def post(self,request,doctor_id):
        return Response(doctor_payload(restore_doctor(current_actor(request),doctor_id,edit_revision(request)),current_actor(request)))

class DoctorEnabledView(APIView):
    def post(self,request,doctor_id):
        if not isinstance(request.data.get('enabled'),bool):raise ApiError('validation_error','启用状态不正确',status=400)
        return Response(doctor_payload(set_doctor_enabled(current_actor(request),doctor_id,request.data['enabled'],edit_revision(request)),current_actor(request)))

class DoctorOptionsView(APIView):
    def get(self,request):
        actor=current_actor(request);require_tenant(actor)
        query=Doctor.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=True).order_by('name','id')
        return Response({'count':query.count(),'results':[{'id':str(d.id),'name':d.name} for d in query]})
