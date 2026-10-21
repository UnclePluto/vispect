import hashlib
import json
from django.db import connection,transaction
from django.utils import timezone
from apps.core.errors import ApiError
from apps.core.helpers import ensure_revision
from apps.followups.models import Answer
from apps.followups.answers import evaluated
from apps.followups.authorship import set_answer_recorder,stamp_answer_submission
from .models import PatientSubmissionReceipt
from .tasks import locked_patient_task,task_state
from .activity import record_patient_activity


def payload_digest(entry,visit,binding,patient_id,answers,expected_revision):
    payload={'entry':str(entry.id),'visit':str(visit.id),'binding':str(binding.id),'patient':str(patient_id),'answers':answers,'expected_revision':expected_revision,'action':'submit'}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def write_patient_answer(principal,entry_token,patient_id,answers,expected_revision,*,key=None):
    submitting=key is not None
    with transaction.atomic():
        if submitting:
            if not isinstance(key,str) or not key or len(key)>128:raise ApiError('idempotency_key_required','正式提交需要有效的重试标识',status=400)
            lock=int.from_bytes(hashlib.sha256(f'vispect.patient.receipt:{principal.identity_id}:{key}'.encode()).digest()[:8],'big',signed=True)
            with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_xact_lock(%s)',[lock])
        entry,visit,binding=locked_patient_task(principal,entry_token,patient_id)
        if submitting:
            digest=payload_digest(entry,visit,binding,patient_id,answers,expected_revision)
            old=PatientSubmissionReceipt.objects.filter(identity_id=principal.identity_id,key=key).first()
            if old:
                if old.payload_digest!=digest:raise ApiError('idempotency_key_reused','该重试标识已用于不同内容，请刷新后重试',status=409)
                return Answer.objects.select_related('recorded_by','recorded_by_patient','submitted_by','submitted_by_patient').get(id=old.answer_id,visit_id=visit.id,binding_id=binding.id,deleted_at__isnull=True)
        answer=Answer.objects.select_for_update().filter(visit_id=visit.id,binding_id=binding.id).first()
        state,writable,reason=task_state(visit,binding,answer)
        if not writable:raise ApiError('task_read_only',reason or '当前表单只读',status=409)
        clean=evaluated(binding,answers,'submit' if submitting else 'draft')
        if answer:ensure_revision(answer,expected_revision)
        elif expected_revision!=0:raise ApiError('revision_conflict','答案草稿已变化，请刷新后重试',status=409)
        if answer:
            answer.answers=clean;answer.revision+=1
        else:
            answer=Answer(tenant_id=principal.tenant_id,visit_id=visit.id,stage_id=visit.stage_id,binding_id=binding.id,form_version_id=binding.form_version_id,respondent='patient',answers=clean)
        set_answer_recorder(answer,patient_identity_id=principal.identity_id)
        if submitting:
            answer.status='submitted';answer.submitted_at=timezone.now();stamp_answer_submission(answer)
        answer.save()
        record_patient_activity(principal,'submit' if submitting else 'save_draft',answer.id,{'visit_id':str(visit.id),'binding_id':str(binding.id),'revision':answer.revision})
        if submitting:PatientSubmissionReceipt.objects.create(tenant_id=principal.tenant_id,identity_id=principal.identity_id,key=key,payload_digest=digest,answer_id=answer.id)
        return answer


def save_patient_answer(principal,entry_token,patient_id,answers,expected_revision):
    return write_patient_answer(principal,entry_token,patient_id,answers,expected_revision)


def submit_patient_answer(principal,entry_token,patient_id,answers,expected_revision,key):
    # An absent submit key must never become a draft operation.
    if key is None:key=''
    return write_patient_answer(principal,entry_token,patient_id,answers,expected_revision,key=key)
