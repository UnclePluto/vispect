def test_audit_only_allows_tenant_administrator(world):
    p=world.patient('a');other=world.patient('b')
    response=world.login('a','tenant_admin').get('/api/audit/');assert response.status_code==200
    ids={r['object_id'] for r in response.json()['results']};assert str(p.id) in ids and str(other.id) not in ids
    assert world.login('a','doctor').get('/api/audit/').status_code==403
    assert world.login(None,'platform_admin').get('/api/audit/').status_code==403

def test_platform_audit_only_contains_control_events(world):
    world.patient('a');client=world.login(None,'platform_admin')
    response=world.post(client,'/api/platform/tenants/',{'slug':'audit-tenant','name':'平台审计机构','admin_username':'admin','admin_password':world.password,'limits':{'doctors':10,'patients':10,'studies':10}})
    assert response.status_code==201
    data=client.get('/api/platform/audit/');assert data.status_code==200
    assert all(e['tenant_id'] is None for e in data.json()['results'])
    assert 'password' not in str(data.json()).lower()

def test_core_workflow_mutations_leave_audit_events(world):
    from apps.followups.answers import save_answer_draft,submit_answer,revise_answer
    from apps.followups.transitions import complete_visit,stop_followup
    from apps.followups.exports import export_answers
    from apps.patients.services import assign_doctors,update_patient,delete_patient,restore_patient
    from apps.core.context import tenant_transaction
    from apps.core.models import AuditEvent
    e,v,b=world.entry('a');a=world.actor('a','doctor');admin=world.actor('a','tenant_admin')
    draft=save_answer_draft(a,v.id,b.id,{'q1':'草稿'},0);answer=submit_answer(a,v.id,b.id,{'q1':'提交'},'s');revise_answer(a,answer.id,{'q1':'修正'},'纠正',answer.revision)
    complete_visit(a,v.id,'c');stop_followup(a,e.id,'other','停止原因','stop');export_answers(a,study_id=e.study_id)
    with tenant_transaction(a.tenant_id):p=e.patient
    p=update_patient(admin,p.id,{'name':'更名'},p.revision);p=assign_doctors(admin,p.id,[a.doctor_id],p.revision);p=delete_patient(admin,p.id,p.revision);restore_patient(admin,p.id,p.revision)
    with tenant_transaction(a.tenant_id):actions=set(AuditEvent.objects.values_list('action',flat=True))
    assert {'create','update','assign_doctors','publish','protocol','state','add_subject','confirm_enrollment','save_draft','submit','revise','complete','stop','export','delete','restore'}<=actions
