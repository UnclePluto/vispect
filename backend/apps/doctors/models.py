from django.db import models
from apps.core.models import TenantRecord,tenant_identity_constraint

class Doctor(TenantRecord):
    account=models.OneToOneField('accounts.Account',on_delete=models.PROTECT)
    name=models.CharField(max_length=200)
    phone=models.CharField(max_length=40,blank=True)
    organization=models.CharField(max_length=200,blank=True)
    department=models.CharField(max_length=100,blank=True)
    title=models.CharField(max_length=100,blank=True)
    class Meta:
        ordering=['-created_at','id']
        constraints=[tenant_identity_constraint()]
