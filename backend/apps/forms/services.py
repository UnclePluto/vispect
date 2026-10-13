from django.utils import timezone
from apps.core.context import tenant_transaction
from apps.core.permissions import require_tenant,require_role
from apps.core.helpers import get_object,ensure_revision
from apps.core.errors import ApiError
from apps.core.audit import audit
from apps.core.idempotency import run_idempotent
from .definition import validate_definition
from .models import Form,FormVersion
from .selectors import editable_forms

def check_definition(definition,publish=False):
    errors=validate_definition(definition,publish)
    if errors:raise ApiError('invalid_definition','表单定义不完整或规则无效',errors,400)

def create_form(actor,definition):
    require_tenant(actor);check_definition(definition)
    with tenant_transaction(actor.tenant_id):
        form=Form.objects.create(tenant_id=actor.tenant_id,owner_id=actor.account_id,draft_definition=definition)
        audit(actor,'create','form',form.id,{'title':definition['title']});return form

def save_draft(actor,form_id,definition,expected_revision):
    require_tenant(actor);check_definition(definition)
    with tenant_transaction(actor.tenant_id):
        form=get_object(editable_forms(actor),form_id,True);ensure_revision(form,expected_revision)
        form.draft_definition=definition;form.revision+=1;form.save();audit(actor,'save_draft','form',form.id,{'title':definition['title']});return form

def publish_form(actor,form_id,expected_revision,key):
    require_tenant(actor)
    with tenant_transaction(actor.tenant_id):
        form=get_object(editable_forms(actor),form_id,True)
        def mutation():
            ensure_revision(form,expected_revision);check_definition(form.draft_definition,True)
            previous=form.versions.first()
            version=FormVersion.objects.create(tenant_id=actor.tenant_id,form=form,number=previous.number+1 if previous else 1,definition=form.draft_definition,published_by_id=actor.account_id)
            form.revision+=1;form.save();audit(actor,'publish','form',form.id,{'version_id':str(version.id),'number':version.number})
            return {'id':str(version.id)}
        result=run_idempotent(actor,key,'publish_form',{'form_id':str(form_id),'expected_revision':expected_revision},mutation)
        return get_object(FormVersion.objects.filter(form=form),result['id'])

def set_form_paused(actor,form_id,paused,expected_revision):
    require_tenant(actor)
    with tenant_transaction(actor.tenant_id):
        form=get_object(editable_forms(actor),form_id,True);ensure_revision(form,expected_revision)
        form.paused=paused;form.revision+=1;form.save();audit(actor,'pause' if paused else 'resume','form',form.id,{});return form

def delete_form(actor,form_id,expected_revision):
    require_tenant(actor)
    with tenant_transaction(actor.tenant_id):
        form=get_object(editable_forms(actor),form_id,True);ensure_revision(form,expected_revision)
        from apps.studies.models import FormBinding
        if FormBinding.objects.filter(form_version__form=form,stage__study__deleted_at__isnull=True,stage__study__state__in=['active','paused']).exists():
            raise ApiError('form_in_use','该表单被进行中或暂停研究引用')
        form.deleted_at=timezone.now();form.revision+=1;form.save();audit(actor,'delete','form',form.id,{});return form

def restore_form(actor,form_id,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    with tenant_transaction(actor.tenant_id):
        form=get_object(editable_forms(actor,True).filter(deleted_at__isnull=False),form_id,True);ensure_revision(form,expected_revision)
        form.deleted_at=None;form.revision+=1;form.save();audit(actor,'restore','form',form.id,{});return form
