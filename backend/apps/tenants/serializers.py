from rest_framework import serializers
from .quota import RESOURCES

class LimitsSerializer(serializers.Serializer):
    doctors=serializers.IntegerField(min_value=0,max_value=2147483647)
    patients=serializers.IntegerField(min_value=0,max_value=2147483647)
    studies=serializers.IntegerField(min_value=0,max_value=2147483647)

class TenantWriteSerializer(serializers.Serializer):
    slug=serializers.SlugField(max_length=64)
    name=serializers.CharField(max_length=200)
    enabled=serializers.BooleanField(required=False)
    limits=LimitsSerializer(required=False)
    admin_username=serializers.CharField(max_length=150,required=False)
    admin_password=serializers.CharField(trim_whitespace=False,required=False,write_only=True)
    expected_revision=serializers.IntegerField(min_value=1,required=False)

class AdministratorSerializer(serializers.Serializer):
    username=serializers.CharField(max_length=150)
    name=serializers.CharField(max_length=200)
    password=serializers.CharField(trim_whitespace=False,required=False,write_only=True,allow_blank=True)
    enabled=serializers.BooleanField(required=False)
    expected_revision=serializers.IntegerField(min_value=1)

def tenant_payload(tenant):
    quota=tenant.quota
    return {'id':str(tenant.id),'slug':tenant.slug,'name':tenant.name,'enabled':tenant.enabled,'revision':tenant.revision,
        'limits':{r:getattr(quota,f'{r}_limit') for r in RESOURCES},'usage':{r:getattr(quota,f'{r}_used') for r in RESOURCES}}
