def test_dashboard_aggregates_only_visible_data(world):
    world.entry('a');other=world.doctor('a');world.patient('a',doctor_ids=[other.id]);world.study('b')
    doctor=world.login('a','doctor').get('/api/dashboard/');assert doctor.status_code==200
    data=doctor.json();assert data['patients']==1 and data['studies']==1 and data['today_tasks']==1
    assert world.login('a','tenant_admin').get('/api/dashboard/').json()['patients']==2
    assert world.login(None,'platform_admin').get('/api/dashboard/').status_code==403

def test_patient_details_and_form_references_do_not_open_nonmember_studies(world):
    from apps.studies.services import create_study,save_protocol,set_study_state
    from apps.followups.enrollments import add_subject
    a=world.actor('a','doctor');admin=world.actor('a','tenant_admin');other=world.doctor('a');version=world.form_version('a')
    s=create_study(admin,{'name':'其他医生研究','code':'other-study','owner_id':other.id})
    s=save_protocol(admin,s.id,[{'name':'基线','kind':'baseline','offset_days':0,'bindings':[{'form_version_id':str(version.id),'respondent':'patient','required':True}]}],s.revision);s=set_study_state(admin,s.id,'active',s.revision)
    p=world.patient('a',doctor_ids=[a.doctor_id,other.id]);add_subject(admin,s.id,p.id,other.id,'obs','add')
    client=world.login('a','doctor')
    assert client.get(f'/api/patients/{p.id}/').json()['enrollments']==[]
    references=client.get(f'/api/forms/{version.form_id}/references/').json()
    assert references=={'studies':[],'pending_visits':0}
