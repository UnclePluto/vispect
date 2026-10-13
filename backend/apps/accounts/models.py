import uuid
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models import Q

class Account(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', null=True, blank=True, on_delete=models.PROTECT)
    username = models.CharField(max_length=150)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=24, choices=[('platform_admin','超级管理员'),('tenant_admin','租户管理员'),('doctor','医生')])
    doctor_id = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'id'
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant','username'], name='account_tenant_username'),
            models.UniqueConstraint(fields=['username'], condition=Q(tenant__isnull=True), name='account_platform_username'),
            models.UniqueConstraint(fields=['tenant','id'], name='account_tenant_id'),
            models.CheckConstraint(condition=(Q(role='platform_admin',tenant__isnull=True)|Q(role__in=['tenant_admin','doctor'],tenant__isnull=False)), name='account_role_scope'),
        ]
