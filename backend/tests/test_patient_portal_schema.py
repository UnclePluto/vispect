import hashlib
import secrets
import pytest
from django.apps import apps
from django.db import IntegrityError, transaction
from apps.core.context import tenant_transaction


def portal_model(name):
    assert apps.is_installed('apps.patient_portal'), '患者模块尚未注册'
    return apps.get_model('patient_portal', name)


def test_patient_identity_unique_per_tenant(world):
    Identity = portal_model('PatientLoginIdentity')
    with tenant_transaction(world.tenants['a'].id):
        first = Identity.objects.create(tenant_id=world.tenants['a'].id, phone='+8613800000001', password='!')
        with pytest.raises(IntegrityError), transaction.atomic():
            Identity.objects.create(tenant_id=world.tenants['a'].id, phone=first.phone, password='!')
    with tenant_transaction(world.tenants['b'].id):
        other = Identity.objects.create(tenant_id=world.tenants['b'].id, phone='+8613800000001', password='!')
        assert other.id != first.id


def test_patient_access_rejects_cross_tenant_identity(world):
    Identity = portal_model('PatientLoginIdentity')
    Access = portal_model('PatientAccess')
    patient = world.patient('a')
    with tenant_transaction(world.tenants['b'].id):
        identity = Identity.objects.create(tenant_id=world.tenants['b'].id, phone='+8613800000001', password='!')
    with tenant_transaction(world.tenants['a'].id):
        with pytest.raises(IntegrityError), transaction.atomic():
            Access.objects.create(tenant_id=world.tenants['a'].id, patient_id=patient.id, identity_id=identity.id)


def test_scope_functions_return_metadata_only(world):
    Entry = portal_model('PatientFormEntry')
    from apps.patient_portal.scope_store import resolve_entry_scope
    _, _, binding = world.entry('a')
    raw = secrets.token_urlsafe(32)
    with tenant_transaction(world.tenants['a'].id):
        entry = Entry.objects.create(tenant_id=world.tenants['a'].id, binding_id=binding.id, token=raw, token_digest=hashlib.sha256(raw.encode()).hexdigest(), created_by_id=world.actor('a','doctor').account_id)
    assert resolve_entry_scope(raw) == (entry.tenant_id, entry.id)
    from apps.core.errors import ApiError
    with pytest.raises(ApiError) as error:
        resolve_entry_scope('unknown')
    assert error.value.status == 404


def test_patient_tables_are_cleaned_between_worlds(world):
    Identity=portal_model('PatientLoginIdentity')
    with tenant_transaction(world.tenants['a'].id):
        assert Identity.objects.count() == 0
