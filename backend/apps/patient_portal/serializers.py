from rest_framework import serializers
from apps.core.errors import ApiError

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self,data):
        if not isinstance(data,dict):raise serializers.ValidationError('请求内容必须为对象')
        if set(data)-set(self.fields):raise ApiError('forbidden_fields','包含不支持的字段',status=400)
        return super().to_internal_value(data)

class OpenAccessSerializer(StrictSerializer):
    phone=serializers.CharField(max_length=40)
    expected_revision=serializers.IntegerField(min_value=1)

class PatientAnswerWriteSerializer(StrictSerializer):
    action=serializers.ChoiceField(choices=['draft','submit'])
    answers=serializers.JSONField()
    expected_revision=serializers.IntegerField(min_value=0)
