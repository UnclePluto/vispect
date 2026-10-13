import uuid
from django.db import models

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TenantQuota(models.Model):
    tenant = models.OneToOneField(Tenant, primary_key=True, on_delete=models.PROTECT, related_name='quota')
    doctors_limit = models.PositiveIntegerField(default=100)
    patients_limit = models.PositiveIntegerField(default=1000)
    studies_limit = models.PositiveIntegerField(default=100)
    doctors_used = models.PositiveIntegerField(default=0)
    patients_used = models.PositiveIntegerField(default=0)
    studies_used = models.PositiveIntegerField(default=0)
    lock_marker = models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(**{f'{r}_used__lte':models.F(f'{r}_limit')}),name=f'{r}_usage_within_limit') for r in ['doctors','patients','studies']]
