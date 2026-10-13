from django.db import models
from apps.core.models import TenantRecord,tenant_identity_constraint
class Enrollment(TenantRecord):
    study=models.ForeignKey('studies.Study',on_delete=models.PROTECT,related_name='enrollments')
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,related_name='enrollments')
    doctor=models.ForeignKey('doctors.Doctor',on_delete=models.PROTECT)
    observation_code=models.CharField(max_length=100)
    enrollment_code=models.CharField(max_length=100,null=True,blank=True)
    added_on=models.DateField()
    enrolled_on=models.DateField(null=True,blank=True)
    state=models.CharField(max_length=30,default='awaiting_enrollment',choices=[('screening','筛选中'),('awaiting_enrollment','待入组'),('following','随访中'),('completed','已完成'),('stopped','已停止')])
    current_visit=models.ForeignKey('VisitInstance',null=True,blank=True,on_delete=models.PROTECT,related_name='+')
    stopped_on=models.DateTimeField(null=True,blank=True)
    stop_type=models.CharField(max_length=40,blank=True)
    stop_reason=models.TextField(blank=True)
    class Meta:
        ordering=['-created_at','id']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['study','patient'],name='study_patient_once'),models.UniqueConstraint(fields=['study','observation_code'],name='study_observation_code'),models.UniqueConstraint(fields=['study','enrollment_code'],name='study_enrollment_code'),models.UniqueConstraint(fields=['tenant','id','study'],name='enrollment_tenant_id_study')]
class VisitInstance(TenantRecord):
    study=models.ForeignKey('studies.Study',on_delete=models.PROTECT)
    enrollment=models.ForeignKey(Enrollment,on_delete=models.PROTECT,related_name='visits')
    stage=models.ForeignKey('studies.VisitDefinition',on_delete=models.PROTECT)
    planned_on=models.DateField()
    window_start=models.DateField()
    window_end=models.DateField()
    status=models.CharField(max_length=20,default='pending',choices=[('pending','待完成'),('completed','已完成'),('stopped','已停止')])
    completed_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        ordering=['planned_on','id']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['enrollment','stage'],name='enrollment_stage_once'),models.UniqueConstraint(fields=['tenant','enrollment','id'],name='visit_tenant_enrollment_id')]
