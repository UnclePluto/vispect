from apps.core.errors import ApiError
from apps.core.helpers import get_object
from apps.patients.models import Patient
from apps.studies.models import Study,FormBinding
from apps.forms.models import Form
from apps.followups.models import Enrollment,VisitInstance,Answer
from apps.followups.serializers import answer_payload
from apps.tenants.models import TenantQuota
from .models import PatientAccess,PatientFormEntry
from .scope_store import resolve_entry_scope


def authorized_entry(principal,token):
    tenant_id,entry_id=resolve_entry_scope(token)
    if tenant_id!=principal.tenant_id:raise ApiError('entry_login_required','请登录此填写入口所属机构的患者账号',status=401)
    return get_object(PatientFormEntry.objects.filter(tenant_id=principal.tenant_id,enabled=True,deleted_at__isnull=True,binding__respondent='patient',binding__stage__study__deleted_at__isnull=True,binding__form_version__form__deleted_at__isnull=True).exclude(binding__stage__kind='screening').select_related('binding__stage__study','binding__form_version__form'),entry_id)


def authorized_enrollments(principal,entry):
    patient_ids=PatientAccess.objects.filter(tenant_id=principal.tenant_id,identity_id=principal.identity_id,deleted_at__isnull=True,patient__deleted_at__isnull=True).values('patient_id')
    return Enrollment.objects.filter(tenant_id=principal.tenant_id,study_id=entry.binding.stage.study_id,patient_id__in=patient_ids,enrolled_on__isnull=False,deleted_at__isnull=True).select_related('patient','study')


def task_state(visit,binding,answer):
    e=visit.enrollment;study=e.study;form=binding.form_version.form
    if study.state=='paused':state,reason='study_paused','研究已暂停，当前只读'
    elif study.state!='active':state,reason='study_ended','研究已结束，当前只读'
    elif e.state=='stopped' or visit.status=='stopped':state,reason='followup_stopped','随访已停止，当前只读'
    elif form.paused:state,reason='form_paused','表单已暂停，当前只读'
    elif e.state=='completed':state,reason='followup_completed','随访已完成，当前只读'
    elif visit.status=='completed':state,reason='visit_completed','该访视已完成，不能补填'
    elif e.state!='following' or e.current_visit_id!=visit.id:state,reason='not_open','该访视尚未开放'
    else:state,reason='writable',None
    if answer and answer.status=='submitted':return 'submitted',False,reason or '答案已提交，修改请联系医生'
    return state,state=='writable',reason


def resolve_patient_tasks(principal,entry_token):
    entry=authorized_entry(principal,entry_token);results=[]
    for e in authorized_enrollments(principal,entry).order_by('patient__code','patient_id'):
        visit=VisitInstance.objects.filter(enrollment_id=e.id,stage_id=entry.binding.stage_id,deleted_at__isnull=True).first()
        if not visit:continue
        visit.enrollment=e
        answer=Answer.objects.filter(visit_id=visit.id,binding_id=entry.binding_id,deleted_at__isnull=True).first()
        state,_,_=task_state(visit,entry.binding,answer)
        results.append({'patient_id':str(e.patient_id),'patient_name':e.patient.name,'patient_code':e.patient.code,'task_state':state})
    return results


def get_patient_task(principal,entry_token,patient_id):
    entry=authorized_entry(principal,entry_token)
    e=authorized_enrollments(principal,entry).filter(patient_id=patient_id).first()
    if not e:raise ApiError('object_unavailable','暂无对应填写任务，请联系医生',status=404)
    visit=VisitInstance.objects.filter(enrollment_id=e.id,stage_id=entry.binding.stage_id,deleted_at__isnull=True).first()
    if not visit:raise ApiError('object_unavailable','暂无对应填写任务，请联系医生',status=404)
    visit.enrollment=e;binding=entry.binding
    answer=Answer.objects.filter(visit_id=visit.id,binding_id=binding.id,deleted_at__isnull=True).select_related('recorded_by','recorded_by_patient','submitted_by','submitted_by_patient').first()
    state,writable,reason=task_state(visit,binding,answer)
    return {'patient_id':str(e.patient_id),'patient_name':e.patient.name,'patient_code':e.patient.code,'study_name':e.study.name,'stage_name':visit.stage.name,'form_version_id':str(binding.form_version_id),'definition':binding.form_version.definition,'answer':answer_payload(answer) if answer else None,'task_state':state,'writable':writable,'read_only_reason':reason}


def locked_patient_task(principal,entry_token,patient_id):
    entry=authorized_entry(principal,entry_token)
    visible=authorized_enrollments(principal,entry).filter(patient_id=patient_id).first()
    if not visible:raise ApiError('object_unavailable','暂无对应填写任务，请联系医生',status=404)
    TenantQuota.objects.select_for_update().get(tenant_id=principal.tenant_id)
    study=get_object(Study.objects.filter(tenant_id=principal.tenant_id,deleted_at__isnull=True),visible.study_id,True)
    patient=get_object(Patient.objects.filter(tenant_id=principal.tenant_id,deleted_at__isnull=True),visible.patient_id,True,no_key=True)
    e=get_object(Enrollment.objects.filter(tenant_id=principal.tenant_id,deleted_at__isnull=True),visible.id,True);e.study=study;e.patient=patient
    visit=VisitInstance.objects.select_for_update().filter(enrollment_id=e.id,stage_id=entry.binding.stage_id,deleted_at__isnull=True).first()
    if not visit:raise ApiError('object_unavailable','暂无对应填写任务，请联系医生',status=404)
    visit.enrollment=e
    get_object(Form.objects.filter(tenant_id=principal.tenant_id,deleted_at__isnull=True),entry.binding.form_version.form_id,True,no_key=True)
    binding=FormBinding.objects.select_for_update(of=('self',)).select_related('form_version__form','stage').get(id=entry.binding_id)
    entry=get_object(PatientFormEntry.objects.filter(tenant_id=principal.tenant_id,enabled=True,deleted_at__isnull=True),entry.id,True)
    return entry,visit,binding
