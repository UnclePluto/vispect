import uuid
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models import Q
from apps.core.models import TenantRecord, tenant_identity_constraint


class PatientLoginIdentity(AbstractBaseUser, TenantRecord):
    phone = models.CharField(max_length=14)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=True)
    credential_version = models.PositiveIntegerField(default=1)
    USERNAME_FIELD = 'phone'
    class Meta:
        constraints = [tenant_identity_constraint(), models.UniqueConstraint(fields=['tenant','phone'], name='patient_login_tenant_phone')]


class PatientAccess(TenantRecord):
    patient = models.OneToOneField('patients.Patient', on_delete=models.PROTECT, related_name='portal_access')
    identity = models.ForeignKey(PatientLoginIdentity, on_delete=models.PROTECT, related_name='accesses')
    class Meta:
        constraints = [tenant_identity_constraint()]


class PatientFormEntry(TenantRecord):
    binding = models.ForeignKey('studies.FormBinding', on_delete=models.PROTECT, related_name='patient_entries')
    token = models.CharField(max_length=128)
    token_digest = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey('accounts.Account', on_delete=models.PROTECT, related_name='+')
    disabled_by = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    disabled_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at','id']
        constraints = [tenant_identity_constraint(), models.UniqueConstraint(fields=['binding'], condition=Q(enabled=True,deleted_at__isnull=True), name='patient_binding_enabled_entry')]


class PatientSession(TenantRecord):
    identity = models.ForeignKey(PatientLoginIdentity, on_delete=models.PROTECT)
    credential_digest = models.CharField(max_length=64, unique=True)
    credential_version = models.PositiveIntegerField()
    context_token = models.UUIDField(default=uuid.uuid4)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    class Meta:
        constraints = [tenant_identity_constraint()]


class PatientSubmissionReceipt(TenantRecord):
    identity = models.ForeignKey(PatientLoginIdentity, on_delete=models.PROTECT)
    key = models.CharField(max_length=128)
    payload_digest = models.CharField(max_length=64)
    answer = models.ForeignKey('followups.Answer', on_delete=models.PROTECT)
    class Meta:
        constraints = [tenant_identity_constraint(), models.UniqueConstraint(fields=['identity','key'], name='patient_receipt_identity_key')]


class PatientActivity(TenantRecord):
    identity = models.ForeignKey(PatientLoginIdentity, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    object_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    class Meta:
        ordering = ['-created_at','id']
        constraints = [tenant_identity_constraint()]
