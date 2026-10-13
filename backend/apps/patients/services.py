from django.utils import timezone
from apps.core.permissions import require_tenant,require_role
from apps.core.helpers import get_object,ensure_revision
from apps.core.audit import audit
from apps.core.errors import ApiError
from apps.tenants.quota import mutate_with_quota
from apps.doctors.models import Doctor
from .models import Patient,PatientDoctor
from .selectors import visible_patients
FIELDS={'code','name','gender','birth_date','phone','notes','status'}

def validate_doctors(actor,ids):
    ids=set(str(i) for i in ids)
    doctors=list(Doctor.objects.filter(tenant_id=actor.tenant_id,id__in=ids,deleted_at__isnull=True).select_for_update(no_key=True))
    if not ids or len(doctors)!=len(ids):raise ApiError('invalid_doctors','请选择至少一名本机构未删除医生',{'doctor_ids':['负责医生无效']},400)
    return doctors

def replace_doctors(actor,patient,doctors):
    PatientDoctor.objects.filter(patient=patient).delete()
    PatientDoctor.objects.bulk_create([PatientDoctor(tenant_id=actor.tenant_id,patient=patient,doctor=d) for d in doctors])

def create_patient(actor,data):
    require_tenant(actor)
    if actor.role=='doctor' and 'doctor_ids' in data:raise ApiError('forbidden_fields','医生不能分配负责关系',status=400)
    def mutation():
        doctors=validate_doctors(actor,[actor.doctor_id] if actor.role=='doctor' else data.get('doctor_ids',[]))
        patient=Patient.objects.create(tenant_id=actor.tenant_id,**{k:v for k,v in data.items() if k in FIELDS})
        replace_doctors(actor,patient,doctors);audit(actor,'create','patient',patient.id,{'code':patient.code})
        return patient
    return mutate_with_quota(actor,'patients',mutation)

def update_patient(actor,patient_id,data,expected_revision):
    require_tenant(actor)
    if set(data)-FIELDS:raise ApiError('forbidden_fields','包含不可修改的字段',status=400)
    def mutation():
        patient=get_object(visible_patients(actor),patient_id,True);ensure_revision(patient,expected_revision)
        for k,v in data.items():setattr(patient,k,v)
        patient.revision+=1;patient.save();audit(actor,'update','patient',patient.id,{k:str(v) if v is not None else None for k,v in data.items()})
        return patient
    return mutate_with_quota(actor,'patients',mutation,delta=0)

def assign_doctors(actor,patient_id,doctor_ids,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    def mutation():
        patient=get_object(visible_patients(actor),patient_id,True);ensure_revision(patient,expected_revision)
        doctors=validate_doctors(actor,doctor_ids)
        from apps.followups.models import Enrollment
        from apps.followups.selectors import ACTIVE_STATES
        if Enrollment.objects.filter(patient=patient,state__in=ACTIVE_STATES).exclude(doctor_id__in=[d.id for d in doctors]).exists():
            raise ApiError('followup_transfer_required','请先转交该医生尚未结束的随访职责')
        replace_doctors(actor,patient,doctors)
        patient.revision+=1;patient.save();patient._prefetched_objects_cache={}
        audit(actor,'assign_doctors','patient',patient.id,{'doctor_ids':[str(d.id) for d in doctors]});return patient
    return mutate_with_quota(actor,'patients',mutation,delta=0)

def delete_patient(actor,patient_id,expected_revision):
    require_tenant(actor)
    def mutation():
        patient=get_object(visible_patients(actor),patient_id,True);ensure_revision(patient,expected_revision)
        from apps.followups.models import Enrollment
        from apps.followups.selectors import ACTIVE_STATES
        if Enrollment.objects.filter(patient=patient,state__in=ACTIVE_STATES).exists():
            raise ApiError('patient_has_followups','请先完成或停止进行中的随访')
        patient.deleted_at=timezone.now();patient.revision+=1;patient.save();audit(actor,'delete','patient',patient.id,{});return patient
    return mutate_with_quota(actor,'patients',mutation,delta=-1)

def restore_patient(actor,patient_id,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    def mutation():
        patient=get_object(visible_patients(actor,True).filter(deleted_at__isnull=False),patient_id,True);ensure_revision(patient,expected_revision)
        validate_doctors(actor,patient.responsibilities.values_list('doctor_id',flat=True))
        patient.deleted_at=None;patient.revision+=1;patient.save();audit(actor,'restore','patient',patient.id,{});return patient
    return mutate_with_quota(actor,'patients',mutation)
