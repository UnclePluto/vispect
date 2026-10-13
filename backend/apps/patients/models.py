from django.db import models
from apps.core.models import TenantRecord,tenant_identity_constraint

class Patient(TenantRecord):
    code=models.CharField(max_length=100)
    name=models.CharField(max_length=200)
    gender=models.CharField(max_length=20,default='unknown',choices=[('unknown','未知'),('male','男'),('female','女'),('other','其他')])
    birth_date=models.DateField(null=True,blank=True)
    phone=models.CharField(max_length=40,blank=True)
    notes=models.TextField(blank=True)
    status=models.CharField(max_length=20,default='active',choices=[('active','在管'),('inactive','非在管')])
    class Meta:
        ordering=['-created_at','id']
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['tenant','code'],name='patient_tenant_code')]

class PatientDoctor(TenantRecord):
    patient=models.ForeignKey(Patient,on_delete=models.PROTECT,related_name='responsibilities')
    doctor=models.ForeignKey('doctors.Doctor',on_delete=models.PROTECT,related_name='patient_responsibilities')
    class Meta:
        constraints=[tenant_identity_constraint(),models.UniqueConstraint(fields=['patient','doctor'],name='patient_doctor_unique')]
