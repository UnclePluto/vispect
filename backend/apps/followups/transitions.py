from django.utils import timezone
from apps.core.permissions import require_tenant
from apps.core.errors import ApiError
from apps.core.helpers import get_object
from apps.core.audit import audit
from apps.core.idempotency import run_idempotent
from apps.tenants.quota import mutate_with_quota
from .answers import locked_visit,require_writable
from .enrollments import locked_enrollment,require_active
from .models import Answer
from .selectors import visible_visits,visible_enrollments,ACTIVE_STATES

def complete_visit(actor,visit_id,key):
    require_tenant(actor)
    def operation():
        visit,e,study=locked_visit(actor,visit_id);require_active(study)
        def mutation():
            require_writable(visit,e,study)
            required=set(visit.stage.bindings.filter(required=True).values_list('id',flat=True))
            submitted=set(Answer.objects.filter(visit=visit,status='submitted').values_list('binding_id',flat=True))
            if required-submitted:raise ApiError('required_forms_incomplete','请先提交当前访视全部必需表单')
            visit.status='completed';visit.completed_at=timezone.now();visit.revision+=1;visit.save()
            if visit.stage.kind=='screening':e.state='awaiting_enrollment'
            else:
                next_visit=e.visits.filter(stage__position__gt=visit.stage.position,status='pending').order_by('stage__position').first()
                e.current_visit=next_visit
                if next_visit is None:e.state='completed'
            e.revision+=1;e.save();audit(actor,'complete','visit',visit.id,{'enrollment_id':str(e.id),'enrollment_state':e.state});return {'id':str(visit.id)}
        result=run_idempotent(actor,key,'complete_visit',{'visit_id':str(visit_id)},mutation)
        return get_object(visible_visits(actor),result['id'])
    return mutate_with_quota(actor,'studies',operation,delta=0)

def stop_followup(actor,enrollment_id,stop_type,reason,key):
    require_tenant(actor)
    if stop_type not in ['withdrawal','lost','ineligible','other'] or not isinstance(reason,str) or not reason.strip() or len(reason)>10000:raise ApiError('stop_reason_required','请选择停止类型并填写原因',status=400)
    def operation():
        e,study,patient=locked_enrollment(actor,enrollment_id)
        if study.state not in ['active','paused']:raise ApiError('study_read_only','研究当前不允许停止随访')
        def mutation():
            if e.state not in ACTIVE_STATES:raise ApiError('followup_read_only','该受试者随访已结束')
            e.visits.filter(status='pending').update(status='stopped',revision=models.F('revision')+1)
            e.state='stopped';e.current_visit=None;e.stopped_on=timezone.now();e.stop_type=stop_type;e.stop_reason=reason.strip();e.revision+=1;e.save()
            audit(actor,'stop','enrollment',e.id,{'stop_type':stop_type,'reason':reason.strip()});return {'id':str(e.id)}
        result=run_idempotent(actor,key,'stop_followup',{'enrollment_id':str(enrollment_id),'stop_type':stop_type,'reason':reason.strip()},mutation)
        return get_object(visible_enrollments(actor),result['id'])
    return mutate_with_quota(actor,'studies',operation,delta=0)
from django.db import models
