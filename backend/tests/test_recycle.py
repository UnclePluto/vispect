from apps.core.context import tenant_transaction

def test_restore_preserves_stopped_state_and_checks_quota(world):
    from apps.followups.transitions import stop_followup
    from apps.studies.services import set_study_state,delete_study
    from apps.patients.services import delete_patient
    from apps.tenants.models import TenantQuota
    e,v,b=world.entry('a');a=world.actor('a','doctor');admin=world.actor('a','tenant_admin');e=stop_followup(a,e.id,'other','模拟停止','stop')
    with tenant_transaction(a.tenant_id):s=e.study;p=e.patient
    s=set_study_state(a,s.id,'ended',s.revision);s=delete_study(a,s.id,s.revision);p=delete_patient(admin,p.id,p.revision)
    client=world.login('a','tenant_admin');records=client.get('/api/recycle/');assert records.status_code==200
    assert {r['resource'] for r in records.json()['results']}=={'patient','study'}
    assert world.login('a','doctor').get('/api/recycle/').status_code==403
    assert world.login('b','tenant_admin').get('/api/recycle/').json()['count']==0
    restored=world.post(client,f'/api/studies/{s.id}/restore/',{'expected_revision':s.revision});assert restored.json()['state']=='ended'
    quota=TenantQuota.objects.using('migration').get(tenant_id=a.tenant_id);quota.patients_limit=0;world.owner_save(quota)
    assert world.post(client,f'/api/patients/{p.id}/restore/',{'expected_revision':p.revision}).status_code==409
    quota.patients_limit=100;world.owner_save(quota)
    assert world.post(client,f'/api/patients/{p.id}/restore/',{'expected_revision':p.revision}).status_code==200
    assert client.get(f'/api/enrollments/{e.id}/').json()['state']=='stopped'
