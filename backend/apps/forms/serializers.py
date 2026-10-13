from rest_framework import serializers
class DefinitionSerializer(serializers.Serializer):
    definition=serializers.JSONField()

def version_payload(version):
    return {'id':str(version.id),'form_id':str(version.form_id),'number':version.number,'definition':version.definition,'created_at':version.created_at.isoformat()}

def form_payload(form,actor):
    editable=actor.role=='tenant_admin' or form.owner_id==actor.account_id
    version=form.versions.first();definition=form.draft_definition if editable else version.definition
    data={'id':str(form.id),'title':definition['title'],'description':definition.get('description',''),'revision':form.revision,'paused':form.paused,'editable':editable,'owner_id':str(form.owner_id),'latest_version':version_payload(version) if version else None,'updated_at':form.updated_at.isoformat(),'deleted_at':form.deleted_at.isoformat() if form.deleted_at else None}
    if editable:data['draft_definition']=form.draft_definition
    return data
