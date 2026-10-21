from rest_framework import serializers
from django.utils import timezone
from apps.core.errors import ApiError

class PatientWriteSerializer(serializers.Serializer):
    code=serializers.CharField(max_length=100)
    name=serializers.CharField(max_length=200)
    gender=serializers.ChoiceField(choices=['unknown','male','female','other'],required=False)
    birth_date=serializers.DateField(allow_null=True,required=False)
    phone=serializers.CharField(max_length=40,allow_blank=True,required=False)
    notes=serializers.CharField(max_length=10000,allow_blank=True,required=False)
    status=serializers.ChoiceField(choices=['active','inactive'],required=False)
    doctor_ids=serializers.ListField(child=serializers.UUIDField(),allow_empty=False,required=False)
    enable_patient_portal=serializers.BooleanField(required=False,default=False)
    login_phone=serializers.CharField(max_length=40,required=False)
    def to_internal_value(self,data):
        if self.partial and ({'enable_patient_portal','login_phone'} & set(data)):raise ApiError('forbidden_fields','请使用患者账号开通入口',status=400)
        if set(data)-set(self.fields):raise ApiError('forbidden_fields','包含不可修改的字段',status=400)
        if 'code' in data and not isinstance(data['code'],str):raise serializers.ValidationError({'code':['档案编号必须为字符串']})
        return super().to_internal_value(data)
    def validate_birth_date(self,value):
        if value and value>timezone.localdate():raise serializers.ValidationError('出生日期不能晚于今天')
        return value

def patient_payload(patient):
    from apps.patient_portal.access import access_payload
    from apps.patient_portal.models import PatientAccess
    access=PatientAccess.objects.select_related("identity").filter(patient_id=patient.id).first()
    today=timezone.localdate();birth=patient.birth_date
    return {'portal_access':access_payload(access) if access else None,'id':str(patient.id),'code':patient.code,'name':patient.name,'gender':patient.gender,'birth_date':birth.isoformat() if birth else None,'age':today.year-birth.year-((today.month,today.day)<(birth.month,birth.day)) if birth else None,'phone':patient.phone,'notes':patient.notes,'status':patient.status,'revision':patient.revision,'deleted_at':patient.deleted_at.isoformat() if patient.deleted_at else None,'doctors':[{'id':str(r.doctor_id),'name':r.doctor.name} for r in patient.responsibilities.all()]}
