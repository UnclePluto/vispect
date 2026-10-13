import uuid
from django.db import models

class TenantRecord(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    tenant=models.ForeignKey('tenants.Tenant',on_delete=models.PROTECT)
    revision=models.PositiveIntegerField(default=1)
    deleted_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        abstract=True

def tenant_identity_constraint():
    return models.UniqueConstraint(fields=['tenant','id'],name='%(app_label)s_%(class)s_tenant_id')

class AuditEvent(TenantRecord):
    tenant=models.ForeignKey('tenants.Tenant',null=True,on_delete=models.PROTECT)
    actor=models.ForeignKey('accounts.Account',on_delete=models.PROTECT)
    action=models.CharField(max_length=80)
    object_type=models.CharField(max_length=80)
    object_id=models.UUIDField()
    changes=models.JSONField(default=dict)
    class Meta:
        ordering=['-created_at','id']
        constraints=[tenant_identity_constraint()]

class OperationReceipt(TenantRecord):
    tenant=models.ForeignKey('tenants.Tenant',null=True,on_delete=models.PROTECT)
    actor=models.ForeignKey('accounts.Account',on_delete=models.PROTECT)
    key=models.CharField(max_length=128)
    operation=models.CharField(max_length=80)
    payload_digest=models.CharField(max_length=64)
    result=models.JSONField()
    class Meta:
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['actor','key'],name='receipt_actor_key')]
