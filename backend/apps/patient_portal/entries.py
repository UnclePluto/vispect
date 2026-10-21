import secrets
from django.utils import timezone
from apps.core.context import tenant_transaction
from apps.core.helpers import get_object,ensure_revision
from apps.core.audit import audit
from apps.core.errors import ApiError
from apps.forms.models import Form
from apps.forms.selectors import visible_forms
from apps.studies.models import FormBinding
from apps.studies.selectors import visible_studies
from apps.followups.models import Enrollment
from .models import PatientFormEntry
from .scope_store import digest_token


def entry_candidates(actor,form_id):
    get_object(visible_forms(actor),form_id)
    return FormBinding.objects.filter(tenant_id=actor.tenant_id,form_version__form_id=form_id,respondent='patient',stage__study_id__in=visible_studies(actor).values('id')).exclude(stage__kind='screening').select_related('form_version__form','stage__study')


def entry_payload(entry):
    return {'id':str(entry.id),'binding_id':str(entry.binding_id),'token':entry.token,'enabled':entry.enabled,'revision':entry.revision,'url_path':f'/patient/fill/{entry.token}','created_at':entry.created_at.isoformat()}


def creation_block(binding):
    study=binding.stage.study
    if study.state!='active':return '研究需要处于进行中状态'
    if binding.stage.kind=='screening' or binding.respondent!='patient':return '只能为非筛选访视的患者表单创建入口'
    if binding.form_version.form.paused or binding.form_version.form.deleted_at:return '表单已暂停或删除'
    if not Enrollment.objects.filter(study_id=study.id,enrolled_on__isnull=False,deleted_at__isnull=True,patient__deleted_at__isnull=True).exists():return '研究须先有正式入组患者'
    return None


def locked_binding(actor,binding_id):
    binding=get_object(FormBinding.objects.filter(tenant_id=actor.tenant_id).select_related('stage__study','form_version__form'),binding_id)
    get_object(visible_studies(actor),binding.stage.study_id,True)
    get_object(Form.objects.filter(tenant_id=actor.tenant_id),binding.form_version.form_id,True,no_key=True)
    return FormBinding.objects.select_for_update(of=('self',)).select_related('stage__study','form_version__form').get(id=binding.id)


def get_or_create_entry(actor,binding_id):
    with tenant_transaction(actor.tenant_id):
        binding=locked_binding(actor,binding_id)
        if binding.respondent!='patient' or binding.stage.kind=='screening':raise ApiError('entry_unavailable','只能为非筛选访视的患者表单创建入口',status=409)
        existing=PatientFormEntry.objects.filter(binding_id=binding.id).first()
        if existing:return existing
        reason=creation_block(binding)
        if reason:raise ApiError('entry_not_available',reason,status=409)
        return create_entry(actor,binding)


def create_entry(actor,binding):
    token=secrets.token_urlsafe(32)
    entry=PatientFormEntry.objects.create(tenant_id=actor.tenant_id,binding_id=binding.id,token=token,token_digest=digest_token(token),created_by_id=actor.account_id)
    audit(actor,'create_patient_entry','form_binding',binding.id,{'entry_id':str(entry.id)})
    return entry


def change_entry(actor,entry_id,action,expected_revision):
    with tenant_transaction(actor.tenant_id):
        visible=get_object(PatientFormEntry.objects.filter(tenant_id=actor.tenant_id),entry_id)
        binding=locked_binding(actor,visible.binding_id)
        entry=get_object(PatientFormEntry.objects.filter(binding_id=binding.id),entry_id,True)
        ensure_revision(entry,expected_revision)
        latest=PatientFormEntry.objects.filter(binding_id=binding.id).first()
        if latest.id!=entry.id:raise ApiError('entry_replaced','入口已经重新生成，请刷新',status=409)
        if action=='regenerate':
            reason=creation_block(binding)
            if reason:raise ApiError('entry_not_available',reason,status=409)
        if entry.enabled:
            entry.enabled=False;entry.disabled_by_id=actor.account_id;entry.disabled_at=timezone.now();entry.revision+=1;entry.save()
            audit(actor,'disable_patient_entry','form_binding',binding.id,{'entry_id':str(entry.id)})
        return create_entry(actor,binding) if action=='regenerate' else entry
