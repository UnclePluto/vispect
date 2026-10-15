import uuid
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models import Q

class LoginIdentity(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=14, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'phone'

class Account(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(LoginIdentity, null=True, blank=True, on_delete=models.PROTECT, related_name='memberships')
    tenant = models.ForeignKey('tenants.Tenant', null=True, blank=True, on_delete=models.PROTECT)
    username = models.CharField(max_length=150)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=24, choices=[('platform_admin','超级管理员'),('tenant_admin','机构管理员'),('doctor','医生')])
    doctor_id = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'id'
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['identity','tenant'], name='identity_organization_membership'),
            models.UniqueConstraint(fields=['identity'], condition=Q(tenant__isnull=True,identity__isnull=False), name='identity_platform_membership'),
            models.UniqueConstraint(fields=['tenant','username'], name='account_tenant_username'),
            models.UniqueConstraint(fields=['username'], condition=Q(tenant__isnull=True), name='account_platform_username'),
            models.UniqueConstraint(fields=['tenant','id'], name='account_tenant_id'),
            models.CheckConstraint(condition=(Q(role='platform_admin',tenant__isnull=True)|Q(role__in=['tenant_admin','doctor'],tenant__isnull=False)), name='account_role_scope'),
        ]

class LoginSessionContext(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(LoginIdentity, on_delete=models.PROTECT)
    active_account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.PROTECT)
    workspace_token = models.UUIDField(default=uuid.uuid4)
    revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
