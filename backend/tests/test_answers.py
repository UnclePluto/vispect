import pytest
from concurrent.futures import ThreadPoolExecutor
from django.db import connections
from apps.core.errors import ApiError
from apps.core.context import tenant_transaction

def test_submission_retry_does_not_overwrite_answer(world):
    from apps.followups.answers import submit_answer,save_answer_draft
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    draft=save_answer_draft(a,v.id,b.id,{'q1':'草稿'},0)
    first=submit_answer(a,v.id,b.id,{'q1':'提交'},'submit',draft.revision);second=submit_answer(a,v.id,b.id,{'q1':'提交'},'submit',draft.revision)
    assert first.id==second.id==draft.id and second.answers==first.answers=={'q1':'提交'}
    assert first.is_proxy and first.respondent=='patient' and first.recorded_by_id==a.account_id
    with pytest.raises(ApiError):submit_answer(a,v.id,b.id,{'q1':'覆盖'},'new-key')
    with pytest.raises(ApiError):save_answer_draft(a,v.id,b.id,{'q1':'覆盖'},first.revision)

def test_completed_visit_answers_are_read_only(world):
    from apps.followups.answers import submit_answer,revise_answer
    from apps.followups.transitions import complete_visit
    e,v,b=world.entry('a');a=world.actor('a','doctor');answer=submit_answer(a,v.id,b.id,{'q1':'原答案'},'submit');complete_visit(a,v.id,'complete')
    client=world.login('a','doctor');response=world.post(client,f'/api/answers/{answer.id}/revise/',{'answers':{'q1':'新答案'},'reason':'纠正','expected_revision':answer.revision})
    assert response.status_code==409
    with pytest.raises(ApiError):submit_answer(a,v.id,b.id,{'q1':'原答案'},'submit')

def test_revision_keeps_previous_answer_and_requires_reason(world):
    from apps.followups.answers import submit_answer,revise_answer
    from apps.followups.models import AnswerRevision
    e,v,b=world.entry('a');a=world.actor('a','doctor');answer=submit_answer(a,v.id,b.id,{'q1':'原答案'},'submit')
    with pytest.raises(ApiError):revise_answer(a,answer.id,{'q1':'修正'},'',answer.revision)
    answer=revise_answer(a,answer.id,{'q1':'修正'},'纠正录入',answer.revision)
    with tenant_transaction(a.tenant_id):history=AnswerRevision.objects.get(answer=answer)
    assert history.previous_answers=={'q1':'原答案'} and history.reason=='纠正录入' and history.actor_id==a.account_id
    assert answer.answers=={'q1':'修正'}

def test_paused_study_and_form_reject_answer_writes(world):
    from apps.followups.answers import submit_answer,save_answer_draft
    from apps.studies.services import set_study_state
    from apps.forms.services import set_form_paused
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    with tenant_transaction(a.tenant_id):study=e.study;form=b.form_version.form
    study=set_study_state(a,study.id,'paused',study.revision)
    with pytest.raises(ApiError):save_answer_draft(a,v.id,b.id,{'q1':'草稿'},0)
    set_study_state(a,study.id,'active',study.revision)
    set_form_paused(world.actor('a','tenant_admin'),form.id,True,form.revision)
    with pytest.raises(ApiError):submit_answer(a,v.id,b.id,{'q1':'提交'},'s')

def test_future_visit_and_unknown_binding_cannot_be_written(world):
    from apps.followups.answers import submit_answer
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    with tenant_transaction(a.tenant_id):future=e.visits.exclude(id=v.id).first();other=world.study('a')
    with tenant_transaction(a.tenant_id):foreign_binding=other.stages.first().bindings.first()
    with pytest.raises(ApiError):submit_answer(a,future.id,b.id,{'q1':'提前'},'future')
    with pytest.raises(ApiError):submit_answer(a,v.id,foreign_binding.id,{'q1':'错绑定'},'other')

def test_concurrent_submit_does_not_duplicate_answer(world):
    from apps.followups.answers import submit_answer
    from apps.followups.models import Answer
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    def submit(_):
        try:return submit_answer(a,v.id,b.id,{'q1':'并发'},'same').id
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(submit,[1,2]))
    assert ids[0]==ids[1]
    with tenant_transaction(a.tenant_id):assert Answer.objects.filter(visit=v,binding=b).count()==1

def test_answer_version_and_immutable_history_database_constraints(world):
    import psycopg
    from apps.followups.answers import submit_answer,revise_answer
    from apps.followups.models import AnswerRevision
    e,v,b=world.entry('a');a=world.actor('a','doctor');answer=submit_answer(a,v.id,b.id,{'q1':'原'},'s');answer=revise_answer(a,answer.id,{'q1':'修正'},'原因',answer.revision)
    other_version=world.form_version('a')
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(a.tenant_id)])
        with pytest.raises(psycopg.errors.ForeignKeyViolation):conn.execute('UPDATE followups_answer SET form_version_id=%s WHERE id=%s',[other_version.id,answer.id])
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(a.tenant_id)])
        with pytest.raises(psycopg.errors.InsufficientPrivilege):conn.execute("UPDATE followups_answerrevision SET reason='篡改' WHERE answer_id=%s",[answer.id])

@pytest.mark.parametrize('expected_revision',[0,1])
def test_stale_submit_cannot_overwrite_saved_draft(world,expected_revision):
    from apps.followups.answers import save_answer_draft
    from apps.followups.models import Answer
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    draft=save_answer_draft(a,v.id,b.id,{'q1':'第一次保存'},0)
    draft=save_answer_draft(a,v.id,b.id,{'q1':'其他工作人员最新保存'},draft.revision)
    client=world.login('a','doctor')
    response=world.post(client,f'/api/visits/{v.id}/answers/',{'binding_id':str(b.id),'answers':{'q1':'旧页面提交'},'action':'submit','expected_revision':expected_revision},HTTP_IDEMPOTENCY_KEY='stale-submit')
    assert response.status_code==409
    assert response.json()['code']=='revision_conflict'
    with tenant_transaction(a.tenant_id):
        saved=Answer.objects.get(id=draft.id)
        assert saved.answers=={'q1':'其他工作人员最新保存'} and saved.status=='draft' and saved.revision==2

def test_submit_requires_explicit_edit_revision(world):
    e,v,b=world.entry('a');client=world.login('a','doctor')
    response=world.post(client,f'/api/visits/{v.id}/answers/',{'binding_id':str(b.id),'answers':{'q1':'提交'},'action':'submit'},HTTP_IDEMPOTENCY_KEY='missing-revision')
    assert response.status_code==400
