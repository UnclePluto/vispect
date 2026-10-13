from rest_framework import serializers
from apps.core.errors import ApiError
class StudyWriteSerializer(serializers.Serializer):
    name=serializers.CharField(max_length=200)
    code=serializers.CharField(max_length=100)
    organization=serializers.CharField(max_length=200,required=False,allow_blank=True)
    description=serializers.CharField(max_length=10000,required=False,allow_blank=True)
    owner_id=serializers.UUIDField(required=False)
    planned_start=serializers.DateField(required=False,allow_null=True)
    planned_end=serializers.DateField(required=False,allow_null=True)
    def to_internal_value(self,data):
        if set(data)-set(self.fields):raise ApiError('forbidden_fields','包含不可修改字段',status=400)
        if 'code' in data and not isinstance(data['code'],str):raise serializers.ValidationError({'code':['编号须为字符串']})
        return super().to_internal_value(data)

def study_payload(study,actor,detail=False):
    data={'id':str(study.id),'name':study.name,'code':study.code,'organization':study.organization,'description':study.description,'owner_id':str(study.owner_id),'owner_name':study.owner.name,'planned_start':study.planned_start.isoformat() if study.planned_start else None,'planned_end':study.planned_end.isoformat() if study.planned_end else None,'state':study.state,'protocol_frozen':study.protocol_frozen,'revision':study.revision,'editable':actor.role=='tenant_admin' or study.owner_id==actor.doctor_id,'deleted_at':study.deleted_at.isoformat() if study.deleted_at else None}
    if detail:
        data['members']=[{'id':str(m.doctor_id),'name':m.doctor.name} for m in study.memberships.select_related('doctor')]
        data['stages']=[{'id':str(s.id),'position':s.position,'name':s.name,'kind':s.kind,'offset_days':s.offset_days,'window_before':s.window_before,'window_after':s.window_after,'bindings':[{'id':str(b.id),'form_version_id':str(b.form_version_id),'form_title':b.form_version.definition['title'],'version_number':b.form_version.number,'respondent':b.respondent,'required':b.required} for b in s.bindings.select_related('form_version')]} for s in study.stages.all()]
    return data
