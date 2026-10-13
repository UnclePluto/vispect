from concurrent.futures import ThreadPoolExecutor
import pytest
from django.db import connections
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError

def test_required_hidden_field_does_not_block_completion(world):
    from apps.followups.answers import submit_answer
    from apps.followups.transitions import complete_visit
    definition={'protocol_version':1,'title':'条件表单','questions':[{'id':'q1','type':'radio','title':'选择','options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}]},{'id':'q2','type':'text','title':'隐藏必填','required':True,'condition':{'mode':'all','rules':[{'question_id':'q1','operator':'eq','value':'yes'}]}}]}
    e,v,b=world.entry('a',definition=definition);a=world.actor('a','doctor');submit_answer(a,v.id,b.id,{'q1':'no','q2':'删除旧答案'},'s');visit=complete_visit(a,v.id,'c')
    assert visit.status=='completed'
    with tenant_transaction(a.tenant_id):e.refresh_from_db();assert e.current_visit_id!=v.id

def test_final_visit_completion_finishes_subject(world):
    from apps.followups.answers import submit_answer
    from apps.followups.transitions import complete_visit
    e,v,b=world.entry('a');a=world.actor('a','doctor');submit_answer(a,v.id,b.id,{'q1':'基线'},'s1');complete_visit(a,v.id,'c1')
    with tenant_transaction(a.tenant_id):e.refresh_from_db();last=e.current_visit;binding=last.stage.bindings.first()
    submit_answer(a,last.id,binding.id,{'q1':'后续'},'s2');complete_visit(a,last.id,'c2')
    assert complete_visit(a,last.id,'c2').id==last.id
    with tenant_transaction(a.tenant_id):e.refresh_from_db()
    assert e.state=='completed' and e.current_visit_id is None

def test_stopping_preserves_answers_and_is_irreversible(world):
    from apps.followups.answers import submit_answer,revise_answer
    from apps.followups.transitions import stop_followup
    from apps.followups.enrollments import confirm_enrollment
    e,v,b=world.entry('a');a=world.actor('a','doctor');answer=submit_answer(a,v.id,b.id,{'q1':'保留'},'s');e=stop_followup(a,e.id,'withdrawal','受试者退出','stop')
    assert e.state=='stopped' and e.stop_reason=='受试者退出'
    with tenant_transaction(a.tenant_id):assert not e.visits.filter(status='pending').exists()
    with pytest.raises(ApiError):revise_answer(a,answer.id,{'q1':'修改'},'原因',answer.revision)
    with pytest.raises(ApiError):confirm_enrollment(a,e.id,'new',e.enrolled_on,'restart')

def test_concurrent_complete_and_required_form_guard(world):
    from apps.followups.answers import submit_answer
    from apps.followups.transitions import complete_visit
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    with pytest.raises(ApiError):complete_visit(a,v.id,'c')
    submit_answer(a,v.id,b.id,{'q1':'完成'},'s')
    def complete(_):
        try:return complete_visit(a,v.id,'same').id
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(complete,[1,2]))==[v.id,v.id]

def test_screening_completion_requires_separate_confirmation(world):
    from apps.followups.enrollments import add_subject,confirm_enrollment
    from apps.followups.answers import submit_answer
    from apps.followups.transitions import complete_visit
    s=world.study('a',screening=True);p=world.patient('a');a=world.actor('a','doctor');e=add_subject(a,s.id,p.id,a.doctor_id,'obs','add')
    with tenant_transaction(a.tenant_id):v=e.current_visit;b=v.stage.bindings.first()
    submit_answer(a,v.id,b.id,{'q1':'筛选完成'},'s');complete_visit(a,v.id,'c')
    with tenant_transaction(a.tenant_id):e.refresh_from_db()
    assert e.state=='awaiting_enrollment' and e.enrollment_code is None
    e=confirm_enrollment(a,e.id,'000001',e.added_on,'confirm');assert e.state=='following'

def test_pause_allows_stopping_and_prevents_ending_active_subject(world):
    from apps.studies.services import set_study_state
    from apps.followups.transitions import stop_followup
    e,v,b=world.entry('a');a=world.actor('a','doctor')
    with tenant_transaction(a.tenant_id):s=e.study
    with pytest.raises(ApiError):set_study_state(a,s.id,'ended',s.revision)
    s=set_study_state(a,s.id,'paused',s.revision)
    stop_followup(a,e.id,'other','暂停期间终止','stop')
    assert set_study_state(a,s.id,'ended',s.revision).state=='ended'
