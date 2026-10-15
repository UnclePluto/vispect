from rest_framework import serializers

class ChangePasswordSerializer(serializers.Serializer):
    old_password=serializers.CharField(trim_whitespace=False)
    new_password=serializers.CharField(trim_whitespace=False)

def identity_payload(account):
    tenant=account.tenant if account.tenant_id else None
    return {'account_id':str(account.id),'tenant_id':str(account.tenant_id) if account.tenant_id else None,
        'role':account.role,'doctor_id':str(account.doctor_id) if account.doctor_id else None,
        'name':account.name,'must_change_password':account.must_change_password,
        'tenant':{'id':str(tenant.id),'slug':tenant.slug,'name':tenant.name} if tenant else None}
