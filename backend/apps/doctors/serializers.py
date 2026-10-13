from rest_framework import serializers
from apps.core.errors import ApiError

class DoctorWriteSerializer(serializers.Serializer):
    username=serializers.CharField(max_length=150,required=False)
    password=serializers.CharField(trim_whitespace=False,required=False,write_only=True,allow_blank=True)
    name=serializers.CharField(max_length=200)
    phone=serializers.CharField(max_length=40,allow_blank=True,required=False)
    organization=serializers.CharField(max_length=200,allow_blank=True,required=False)
    department=serializers.CharField(max_length=100,allow_blank=True,required=False)
    title=serializers.CharField(max_length=100,allow_blank=True,required=False)
    enabled=serializers.BooleanField(required=False)
    def to_internal_value(self,data):
        unknown=set(data)-set(self.fields)
        if unknown:raise ApiError('forbidden_fields','包含不可修改的字段',{key:['不可修改'] for key in unknown},400)
        return super().to_internal_value(data)

def doctor_payload(doctor):
    return {'id':str(doctor.id),'name':doctor.name,'username':doctor.account.username,
        'phone':doctor.phone,'organization':doctor.organization,'department':doctor.department,'title':doctor.title,
        'enabled':doctor.account.is_active,'revision':doctor.revision,'created_at':doctor.created_at.isoformat(),
        'deleted_at':doctor.deleted_at.isoformat() if doctor.deleted_at else None}
