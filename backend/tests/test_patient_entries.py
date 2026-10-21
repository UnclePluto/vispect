import pytest
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
from apps.patient_portal.scope_store import resolve_entry_scope
from apps.patient_portal.models import PatientFormEntry


def make_entry(world):
    _,visit,binding=world.entry('a');client=world.login('a','doctor')
    response=world.post(client,f'/api/patient-form-bindings/{binding.id}/entry/',{})
    assert response.status_code==200,response.content
    return client,binding,response.json()


def test_one_shared_entry_per_binding(world):
    client,binding,first=make_entry(world)
    second=world.post(client,f'/api/patient-form-bindings/{binding.id}/entry/',{}).json()
    assert second['id']==first['id']
    assert second['token']==first['token']
    assert len(first['token'])>=43
    with tenant_transaction(world.tenants['a'].id):
        assert PatientFormEntry.objects.filter(binding=binding,enabled=True).count()==1


def test_regeneration_revokes_old_token_atomically(world):
    client,binding,entry=make_entry(world)
    response=world.post(client,f"/api/patient-form-entries/{entry['id']}/regenerate/",{'expected_revision':entry['revision']})
    assert response.status_code==200,response.content
    new=response.json()
    assert new['token']!=entry['token']
    assert new['binding_id']==str(binding.id)
    with pytest.raises(ApiError) as exc:resolve_entry_scope(entry['token'])
    assert exc.value.status==404
    assert str(resolve_entry_scope(new['token'])[1])==new['id']


def test_entry_requires_member_non_screening_and_enrolled_patient(world):
    study=world.study('a',screening=True);client=world.login('a','doctor')
    with tenant_transaction(study.tenant_id):
        screening=study.stages.get(kind='screening').bindings.first()
        baseline=study.stages.get(kind='baseline').bindings.first()
    for binding in [screening,baseline]:
        response=world.post(client,f'/api/patient-form-bindings/{binding.id}/entry/',{})
        assert response.status_code==409,response.content


def test_entry_metadata_is_not_clinical_access(world):
    _,_,entry=make_entry(world)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_setting(\'vispect.tenant_id\',true)')
        assert not cursor.fetchone()[0]
    assert resolve_entry_scope(entry['token'])[0]==world.tenants['a'].id
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM patients_patient')
        assert cursor.fetchone()[0]==0


def test_concurrent_generation_has_one_enabled_entry(world):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from django.db import connections
    from apps.patient_portal.entries import get_or_create_entry
    _,_,binding=world.entry('a');actor=world.actor('a','doctor');gate=Barrier(2)
    def run(_):
        connections.close_all()
        try:
            gate.wait(timeout=10)
            return get_or_create_entry(actor,binding.id).id
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(run,range(2)))
    assert ids[0]==ids[1]


def test_unrelated_study_does_not_appear_in_candidates(world):
    client,binding,_=make_entry(world)
    with tenant_transaction(world.tenants['a'].id):form_id=binding.form_version.form_id
    other=world.doctor('a')
    from apps.core.types import Actor
    from apps.patient_portal.entries import entry_candidates
    actor=Actor(other.account_id,other.tenant_id,'doctor',other.id)
    with tenant_transaction(actor.tenant_id):assert list(entry_candidates(actor,form_id))==[]


def test_empty_entry_response_has_explicit_json_envelope(world):
    _,_,binding=world.entry('a');client=world.login('a','doctor')
    response=client.get(f'/api/patient-form-bindings/{binding.id}/entry/')
    assert response.status_code==200
    assert response.content,'入口未生成也必须返回有效JSON，不能返回空正文'
    assert response.json()=={'entry':None}
