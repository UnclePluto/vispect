import copy
import pytest
import psycopg
from apps.core.context import tenant_transaction
from apps.core.errors import ApiError
DEFINITION={'protocol_version':1,'title':'生活质量','questions':[{'id':'q1','type':'text','title':'感受','required':True}]}

def test_new_version_preserves_old_definition(world):
    from apps.forms.services import create_form,publish_form,save_draft
    from apps.forms.models import FormVersion
    actor=world.actor('a','doctor');form=create_form(actor,DEFINITION)
    v1=publish_form(actor,form.id,1,'publish-1')
    assert publish_form(actor,form.id,1,'publish-1').id==v1.id
    modified=copy.deepcopy(DEFINITION);modified['questions'][0]['title']='新问题'
    form=save_draft(actor,form.id,modified,2);v2=publish_form(actor,form.id,form.revision,'publish-2')
    with tenant_transaction(actor.tenant_id):v1=FormVersion.objects.get(id=v1.id)
    assert v1.definition==DEFINITION and v2.id!=v1.id and v2.number==2
    with psycopg.connect(world.app_dsn) as conn:
        conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(actor.tenant_id)])
        with pytest.raises(psycopg.Error):conn.execute("UPDATE forms_formversion SET definition='{}' WHERE id=%s",[v1.id])

def test_form_draft_owner_and_published_directory(world):
    from apps.forms.services import create_form,publish_form,save_draft
    admin=world.actor('a','tenant_admin');form=create_form(admin,DEFINITION);client=world.login('a','doctor')
    assert client.get(f'/api/forms/{form.id}/').status_code==404
    publish_form(admin,form.id,1,'publish')
    modified=copy.deepcopy(DEFINITION);modified['title']='未发布秘密标题';save_draft(admin,form.id,modified,2)
    detail=client.get(f'/api/forms/{form.id}/').json()
    assert detail['title']=='生活质量' and 'draft_definition' not in detail
    assert client.get('/api/forms/?search=秘密').json()['count']==0
    assert client.get('/api/forms/?search=生活').json()['count']==1
    token=client.get('/api/auth/csrf/').json()['csrf_token']
    assert client.patch(f'/api/forms/{form.id}/',{'definition':DEFINITION,'expected_revision':3},format='json',HTTP_X_CSRFTOKEN=token).status_code==404
    assert world.login('b','tenant_admin').get(f'/api/forms/{form.id}/versions/').status_code==404
    assert world.login(None,'platform_admin').get('/api/forms/').status_code==403

def test_form_pause_revision_delete_restore(world):
    from apps.forms.services import create_form,publish_form,set_form_paused,save_draft,delete_form,restore_form
    actor=world.actor('a','doctor');f=create_form(actor,DEFINITION);v=publish_form(actor,f.id,1,'p')
    with pytest.raises(ApiError) as exc:save_draft(actor,f.id,DEFINITION,1)
    assert exc.value.code=='revision_conflict'
    f=set_form_paused(actor,f.id,True,2)
    client=world.login('a','doctor');assert client.get(f'/api/forms/{f.id}/versions/').json()['results'][0]['id']==str(v.id)
    f=delete_form(actor,f.id,f.revision);assert client.get(f'/api/forms/{f.id}/').status_code==404
    f=restore_form(world.actor('a','tenant_admin'),f.id,f.revision)
    assert f.paused and f.deleted_at is None
