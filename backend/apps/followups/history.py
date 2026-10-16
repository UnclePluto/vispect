from apps.core.helpers import get_object
from .selectors import visible_answers
from .models import AnswerRevision

def visible_answer_revisions(actor,answer_id):
    answer=get_object(visible_answers(actor),answer_id)
    return AnswerRevision.objects.filter(tenant_id=actor.tenant_id,answer=answer).select_related('actor','previous_recorded_by','previous_recorded_by_patient','answer__form_version')

def revision_payload(revision):
    from .serializers import recorder_name
    return {'id':str(revision.id),'answer_id':str(revision.answer_id),'definition':revision.answer.form_version.definition,'new_answers':revision.new_answers,'previous_answers':revision.previous_answers,'previous_revision':revision.previous_revision,'previous_recorded_by_name':recorder_name(revision.previous_recorded_by,revision.previous_recorded_by_patient),'actor_name':revision.actor.name,'reason':revision.reason,'created_at':revision.created_at.isoformat()}
