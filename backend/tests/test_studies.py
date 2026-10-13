import pytest
from apps.core.errors import ApiError
from apps.core.context import tenant_transaction

def protocol(version):
    return [{'name':'基线期','kind':'baseline','offset_days':0,'window_before':0,'window_after':3,'bindings':[{'form_version_id':str(version.id),'respondent':'patient','required':True}]}]

def test_protocol_requires_one_baseline(world):
    from apps.studies.services import create_study
    s=create_study(world.actor('a','doctor'),{'name':'研究','code':'000001'});v=world.form_version('a');client=world.login('a','doctor')
    for stages in [[],[protocol(v)[0],protocol(v)[0]], [{**protocol(v)[0],'kind':'followup'}],[{**protocol(v)[0],'offset_days':2}],[{**protocol(v)[0],'window_before':-1}]]:
        response=world.post(client,f'/api/studies/{s.id}/protocol/',{'stages':stages,'expected_revision':1})
        assert response.status_code==409,response.content

def test_study_members_can_read_but_only_owner_edits(world):
    from apps.studies.services import create_study,set_study_members,save_protocol
    s=create_study(world.actor('a','tenant_admin'),{'name':'研究','code':'study','owner_id':str(world.accounts['a','doctor'].doctor_id)})
    outsider=world.doctor('a');from apps.core.types import Actor
    actor=Actor(outsider.account_id,outsider.tenant_id,'doctor',outsider.id)
    from apps.studies.selectors import visible_studies
    with tenant_transaction(actor.tenant_id):assert not visible_studies(actor).exists()
    s=set_study_members(world.actor('a','doctor'),s.id,[outsider.id],s.revision)
    with tenant_transaction(actor.tenant_id):assert visible_studies(actor).count()==1
    with pytest.raises(ApiError) as exc:save_protocol(actor,s.id,protocol(world.form_version('a')),s.revision)
    assert exc.value.status==404
    assert world.login('b','tenant_admin').get(f'/api/studies/{s.id}/').status_code==404
    assert world.login(None,'platform_admin').get('/api/studies/').status_code==403

def test_study_lifecycle_quota_and_reference_guards(world):
    from apps.studies.services import create_study,save_protocol,set_study_state,delete_study,restore_study
    from apps.forms.services import delete_form
    from apps.doctors.services import delete_doctor
    from apps.tenants.models import TenantQuota
    a=world.actor('a','doctor');admin=world.actor('a','tenant_admin');s=create_study(a,{'name':'研究','code':'study'});v=world.form_version('a')
    with pytest.raises(ApiError):set_study_state(a,s.id,'active',s.revision)
    s=save_protocol(a,s.id,protocol(v),s.revision);s=set_study_state(a,s.id,'active',s.revision)
    with pytest.raises(ApiError) as exc:delete_form(admin,v.form_id,2)
    assert exc.value.code=='form_in_use'
    with pytest.raises(ApiError) as exc:delete_doctor(admin,a.doctor_id,1)
    assert exc.value.code=='doctor_has_studies'
    s=set_study_state(a,s.id,'paused',s.revision);s=set_study_state(a,s.id,'ended',s.revision)
    assert TenantQuota.objects.using('migration').get(tenant=world.tenants['a']).studies_used==1
    with pytest.raises(ApiError):set_study_state(a,s.id,'active',s.revision)
    s=delete_study(a,s.id,s.revision);s=restore_study(admin,s.id,s.revision)
    assert s.state=='ended'

def test_protocol_rejects_cross_tenant_and_invalid_order(world):
    from apps.studies.services import create_study,save_protocol
    a=world.actor('a','doctor');s=create_study(a,{'name':'研究','code':'study'});v=world.form_version('a');foreign=world.form_version('b')
    invalid=[protocol(foreign),[{**protocol(v)[0],'bindings':[]}],protocol(v)+[{**protocol(v)[0],'kind':'screening'}],protocol(v)+[{**protocol(v)[0],'kind':'followup','offset_days':10},{**protocol(v)[0],'kind':'end','offset_days':5}]]
    for stages in invalid:
        with pytest.raises(ApiError):save_protocol(a,s.id,stages,s.revision)
