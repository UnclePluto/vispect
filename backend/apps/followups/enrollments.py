from datetime import date
from django.db import IntegrityError
from apps.core.permissions import require_tenant
from apps.core.helpers import get_object,ensure_revision
from apps.core.errors import ApiError
from apps.core.audit import audit
from apps.core.idempotency import run_idempotent
from apps.tenants.quota import mutate_with_quota
from apps.studies.selectors import visible_studies
from apps.studies.services import validate_protocol,protocol_data
from apps.patients.selectors import visible_patients
from apps.patients.models import PatientDoctor
from apps.doctors.models import Doctor
from apps.studies.models import Study,StudyMember
from .models import Enrollment,VisitInstance
from .selectors import visible_enrollments,ACTIVE_STATES
from .schedule import local_today,schedule_date

def code(value):
    if not isinstance(value,str) or not value.strip() or len(value)>100:raise ApiError('invalid_code','编号须为 1 至 100 字符的文本',status=400)
    return value.strip()

def require_active(study):
    if study.state!='active':raise ApiError('study_not_active','研究需要处于进行中状态')

def validate_followup_doctor(actor,study,patient,doctor_id):
    doctor=get_object(Doctor.objects.filter(tenant_id=actor.tenant_id,deleted_at__isnull=True),doctor_id,True,no_key=True)
    if not StudyMember.objects.filter(study=study,doctor=doctor).exists() or not PatientDoctor.objects.filter(patient=patient,doctor=doctor).exists():raise ApiError('invalid_followup_doctor','负责随访医生须同时为研究成员和患者负责医生')
    return doctor

def create_visit(actor,enrollment,stage,start):
    planned=schedule_date(start,stage.offset_days)
    return VisitInstance.objects.create(tenant_id=actor.tenant_id,study=enrollment.study,enrollment=enrollment,stage=stage,planned_on=planned,window_start=schedule_date(planned,-stage.window_before),window_end=schedule_date(planned,stage.window_after))

def add_subject(actor,study_id,patient_id,doctor_id,observation_code,key):
    require_tenant(actor);observation_code=code(observation_code)
    def operation():
        study=get_object(visible_studies(actor),study_id,True);patient=get_object(visible_patients(actor),patient_id,True,no_key=True);require_active(study)
        doctor=validate_followup_doctor(actor,study,patient,doctor_id)
        if actor.role=='doctor' and doctor.id!=actor.doctor_id:raise ApiError('forbidden_assignment','医生只能为本人创建随访职责',status=403)
        def mutation():
            validate_protocol(actor,protocol_data(study))
            if Enrollment.objects.filter(study=study,patient=patient).exists():raise ApiError('already_enrolled','该患者已加入此研究，不能重复入组')
            if Enrollment.objects.filter(study=study,observation_code=observation_code).exists():raise ApiError('duplicate_code','研究内观察编号已存在')
            screening=study.stages.filter(kind='screening').first()
            e=Enrollment.objects.create(tenant_id=actor.tenant_id,study=study,patient=patient,doctor=doctor,observation_code=observation_code,added_on=local_today(),state='screening' if screening else 'awaiting_enrollment')
            if screening:e.current_visit=create_visit(actor,e,screening,e.added_on);e.save()
            study.protocol_frozen=True;study.revision+=1;study.save();audit(actor,'add_subject','enrollment',e.id,{'study_id':str(study.id),'patient_id':str(patient.id),'doctor_id':str(doctor.id)})
            return {'id':str(e.id)}
        result=run_idempotent(actor,key,'add_subject',{'study_id':str(study_id),'patient_id':str(patient_id),'doctor_id':str(doctor_id),'observation_code':observation_code},mutation)
        return get_object(visible_enrollments(actor),result['id'])
    return mutate_with_quota(actor,'studies',operation,delta=0)

def locked_enrollment(actor,enrollment_id):
    visible=get_object(visible_enrollments(actor),enrollment_id)
    study=get_object(visible_studies(actor),visible.study_id,True)
    patient=get_object(visible_patients(actor),visible.patient_id,True,no_key=True)
    enrollment=get_object(visible_enrollments(actor),enrollment_id,True)
    return enrollment,study,patient

def confirm_enrollment(actor,enrollment_id,enrollment_code,enrolled_on,key):
    require_tenant(actor);enrollment_code=code(enrollment_code)
    if type(enrolled_on)!=date:raise ApiError('invalid_date','请填写有效入组日期',status=400)
    def operation():
        e,study,patient=locked_enrollment(actor,enrollment_id);require_active(study)
        validate_followup_doctor(actor,study,patient,e.doctor_id)
        def mutation():
            if e.state not in ['awaiting_enrollment','screening']:raise ApiError('already_confirmed','当前受试者不能再次确认入组')
            if e.state=='screening' and (not e.current_visit_id or e.current_visit.status!='completed'):raise ApiError('screening_incomplete','请先完成筛选期访视及必需表单')
            if enrolled_on<e.added_on:raise ApiError('invalid_date','入组日期不能早于加入研究日期',status=400)
            if Enrollment.objects.filter(study=study,enrollment_code=enrollment_code).exclude(id=e.id).exists():raise ApiError('duplicate_code','研究内入组编号已存在')
            e.enrollment_code=enrollment_code;e.enrolled_on=enrolled_on;e.state='following'
            visits=[create_visit(actor,e,s,enrolled_on) for s in study.stages.exclude(kind='screening').order_by('position')]
            e.current_visit=visits[0];e.revision+=1;e.save();audit(actor,'confirm_enrollment','enrollment',e.id,{'enrollment_code':enrollment_code,'enrolled_on':enrolled_on.isoformat()});return {'id':str(e.id)}
        result=run_idempotent(actor,key,'confirm_enrollment',{'enrollment_id':str(enrollment_id),'enrollment_code':enrollment_code,'enrolled_on':enrolled_on.isoformat()},mutation)
        return get_object(visible_enrollments(actor),result['id'])
    return mutate_with_quota(actor,'studies',operation,delta=0)

def transfer_followup(actor,enrollment_id,doctor_id,expected_revision):
    require_tenant(actor)
    def mutation():
        e,study,patient=locked_enrollment(actor,enrollment_id);ensure_revision(e,expected_revision)
        if e.state not in ACTIVE_STATES or study.state=='ended':raise ApiError('followup_read_only','已完成或停止的随访不能转交')
        if actor.role!='tenant_admin' and e.doctor_id!=actor.doctor_id:raise ApiError('forbidden_transfer','只有机构管理员或当前随访医生可转交',status=403)
        doctor=validate_followup_doctor(actor,study,patient,doctor_id);e.doctor=doctor;e.revision+=1;e.save();audit(actor,'transfer','enrollment',e.id,{'doctor_id':str(doctor.id)});return e
    return mutate_with_quota(actor,'studies',mutation,delta=0)
