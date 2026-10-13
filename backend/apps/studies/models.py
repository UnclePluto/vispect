from django.db import models
from apps.core.models import TenantRecord,tenant_identity_constraint

class Study(TenantRecord):
    name=models.CharField(max_length=200)
    code=models.CharField(max_length=100)
    organization=models.CharField(max_length=200,blank=True)
    description=models.TextField(blank=True)
    owner=models.ForeignKey('doctors.Doctor',on_delete=models.PROTECT,related_name='owned_studies')
    planned_start=models.DateField(null=True,blank=True)
    planned_end=models.DateField(null=True,blank=True)
    state=models.CharField(max_length=20,default='draft',choices=[('draft','草稿'),('active','进行中'),('paused','暂停'),('ended','已结束')])
    protocol_frozen=models.BooleanField(default=False)
    class Meta:
        ordering=['-created_at','id']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['tenant','code'],name='study_tenant_code')]

class StudyMember(TenantRecord):
    study=models.ForeignKey(Study,on_delete=models.PROTECT,related_name='memberships')
    doctor=models.ForeignKey('doctors.Doctor',on_delete=models.PROTECT)
    class Meta:
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['study','doctor'],name='study_doctor_unique')]

class VisitDefinition(TenantRecord):
    study=models.ForeignKey(Study,on_delete=models.PROTECT,related_name='stages')
    position=models.PositiveIntegerField()
    name=models.CharField(max_length=200)
    kind=models.CharField(max_length=20,choices=[('screening','筛选期'),('baseline','基线期'),('followup','其他访视'),('end','结束期')])
    offset_days=models.IntegerField(default=0)
    window_before=models.PositiveIntegerField(default=0)
    window_after=models.PositiveIntegerField(default=0)
    class Meta:
        ordering=['position']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['study','position'],name='study_stage_position'),models.UniqueConstraint(fields=['tenant','id','study'],name='stage_tenant_id_study')]

class FormBinding(TenantRecord):
    stage=models.ForeignKey(VisitDefinition,on_delete=models.PROTECT,related_name='bindings')
    form_version=models.ForeignKey('forms.FormVersion',on_delete=models.PROTECT)
    respondent=models.CharField(max_length=20,choices=[('doctor','医生'),('patient','患者')])
    required=models.BooleanField(default=True)
    class Meta:
        ordering=['created_at','id']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['stage','form_version','respondent'],name='stage_form_respondent')]
