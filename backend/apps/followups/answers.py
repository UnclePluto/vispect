from django.utils import timezone
from apps.core.permissions import require_tenant
from apps.core.helpers import get_object,ensure_revision
from apps.core.errors import ApiError
from apps.core.audit import audit
from apps.core.idempotency import run_idempotent
from apps.tenants.quota import mutate_with_quota
from apps.forms.models import Form
from apps.forms.engine import evaluate_answers
from apps.studies.models import FormBinding
from .models import Answer,AnswerRevision
from .selectors import visible_visits,visible_answers
from .enrollments import locked_enrollment,require_active

def locked_visit(actor,visit_id):
    visible=get_object(visible_visits(actor),visit_id)
    e,study,patient=locked_enrollment(actor,visible.enrollment_id)
    visit=get_object(visible_visits(actor),visit_id,True)
    return visit,e,study

def require_writable(visit,e,study):
    require_active(study)
    if e.state not in ['screening','following'] or visit.status!='pending' or e.current_visit_id!=visit.id:raise ApiError('visit_read_only','只有当前未完成访视允许填写，已完成或停止记录只读')

def writable_binding(actor,visit,binding_id):
    binding=get_object(FormBinding.objects.filter(tenant_id=actor.tenant_id,stage_id=visit.stage_id).select_related('form_version'),binding_id)
    form=get_object(Form.objects.filter(tenant_id=actor.tenant_id),binding.form_version.form_id,True,no_key=True)
    if form.paused or form.deleted_at:raise ApiError('form_unavailable','表单已暂停或删除，当前禁止保存、提交和修订')
    return binding

def evaluated(binding,answers,mode):
    result=evaluate_answers(binding.form_version.definition,answers,mode)
    if result.errors:raise ApiError('invalid_answers','请检查表单填写内容',result.errors,400)
    return result.answers

def answer_values(actor,visit,binding,answers):
    return {'tenant_id':actor.tenant_id,'visit':visit,'stage_id':visit.stage_id,'binding':binding,'form_version_id':binding.form_version_id,'respondent':binding.respondent,'is_proxy':binding.respondent=='patient','recorded_by_id':actor.account_id,'answers':answers}

def save_answer_draft(actor,visit_id,binding_id,answers,expected_revision):
    require_tenant(actor)
    def mutation():
        visit,e,study=locked_visit(actor,visit_id);require_writable(visit,e,study);binding=writable_binding(actor,visit,binding_id);clean=evaluated(binding,answers,'draft')
        answer=Answer.objects.select_for_update().filter(visit=visit,binding=binding).first()
        if answer:
            ensure_revision(answer,expected_revision)
            if answer.status=='submitted':raise ApiError('answer_submitted','已提交答案请进入修订流程')
            answer.answers=clean;answer.recorded_by_id=actor.account_id;answer.revision+=1;answer.save()
        else:
            if expected_revision!=0:raise ApiError('revision_conflict','答案草稿已变化，请刷新后重试')
            answer=Answer.objects.create(**answer_values(actor,visit,binding,clean))
        audit(actor,'save_draft','answer',answer.id,{'visit_id':str(visit.id),'binding_id':str(binding.id)});return answer
    return mutate_with_quota(actor,'studies',mutation,delta=0)

def submit_answer(actor,visit_id,binding_id,answers,key,expected_revision=0):
    require_tenant(actor)
    def operation():
        visit,e,study=locked_visit(actor,visit_id);require_writable(visit,e,study);binding=writable_binding(actor,visit,binding_id)
        def mutation():
            clean=evaluated(binding,answers,'submit');answer=Answer.objects.select_for_update().filter(visit=visit,binding=binding).first()
            if answer:ensure_revision(answer,expected_revision)
            elif expected_revision!=0:raise ApiError('revision_conflict','答案草稿已变化，请刷新后重试')
            if answer and answer.status=='submitted':raise ApiError('answer_submitted','已提交答案不能覆盖，请填写修订原因')
            if answer:answer.answers=clean;answer.recorded_by_id=actor.account_id;answer.revision+=1
            else:answer=Answer(**answer_values(actor,visit,binding,clean))
            answer.status='submitted';answer.submitted_at=timezone.now();answer.save();audit(actor,'submit','answer',answer.id,{'visit_id':str(visit.id),'binding_id':str(binding.id),'is_proxy':answer.is_proxy});return {'id':str(answer.id)}
        result=run_idempotent(actor,key,'submit_answer',{'visit_id':str(visit_id),'binding_id':str(binding_id),'answers':answers,'expected_revision':expected_revision},mutation)
        return get_object(visible_answers(actor),result['id'])
    return mutate_with_quota(actor,'studies',operation,delta=0)

def revise_answer(actor,answer_id,answers,reason,expected_revision):
    require_tenant(actor)
    if not isinstance(reason,str) or not reason.strip() or len(reason)>10000:raise ApiError('revision_reason_required','修订必须填写有效原因',{'reason':['请填写修订原因']},400)
    def mutation():
        visible=get_object(visible_answers(actor),answer_id);visit,e,study=locked_visit(actor,visible.visit_id);require_writable(visit,e,study)
        binding=writable_binding(actor,visit,visible.binding_id);answer=get_object(visible_answers(actor),answer_id,True);ensure_revision(answer,expected_revision)
        if answer.status!='submitted':raise ApiError('answer_not_submitted','草稿请直接编辑保存')
        clean=evaluated(binding,answers,'submit')
        AnswerRevision.objects.create(tenant_id=actor.tenant_id,answer=answer,previous_answers=answer.answers,previous_revision=answer.revision,previous_recorded_by_id=answer.recorded_by_id,actor_id=actor.account_id,reason=reason.strip())
        answer.answers=clean;answer.recorded_by_id=actor.account_id;answer.revision+=1;answer.save();audit(actor,'revise','answer',answer.id,{'reason':reason.strip(),'revision':answer.revision});return answer
    return mutate_with_quota(actor,'studies',mutation,delta=0)
