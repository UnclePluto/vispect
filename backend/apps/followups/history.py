from apps.core.helpers import get_object
from .selectors import visible_answers
from .models import AnswerRevision

def visible_answer_revisions(actor,answer_id):
    answer=get_object(visible_answers(actor),answer_id)
    return AnswerRevision.objects.filter(tenant_id=actor.tenant_id,answer=answer).select_related('actor','previous_recorded_by')

def revision_payload(revision):
    return {'id':str(revision.id),'answer_id':str(revision.answer_id),'previous_answers':revision.previous_answers,'previous_revision':revision.previous_revision,'previous_recorded_by_name':revision.previous_recorded_by.name,'actor_name':revision.actor.name,'reason':revision.reason,'created_at':revision.created_at.isoformat()}
