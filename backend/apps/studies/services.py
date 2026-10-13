from django.utils import timezone
from apps.core.permissions import require_tenant,require_role
from apps.core.helpers import get_object,ensure_revision
from apps.core.errors import ApiError
from apps.core.audit import audit
from apps.tenants.quota import mutate_with_quota
from apps.patients.services import validate_doctors
from apps.forms.models import Form,FormVersion
from .models import Study,StudyMember,VisitDefinition,FormBinding
from .selectors import visible_studies,editable_studies,require_study_member
FIELDS={'name','code','organization','description','planned_start','planned_end'}

def validate_dates(data,study=None):
    start=data.get('planned_start',getattr(study,'planned_start',None));end=data.get('planned_end',getattr(study,'planned_end',None))
    if start and end and start>end:raise ApiError('invalid_dates','计划结束日期不能早于开始日期',status=400)

def create_study(actor,data):
    require_tenant(actor);validate_dates(data)
    if actor.role=='doctor' and data.get('owner_id') and str(data['owner_id'])!=str(actor.doctor_id):raise ApiError('forbidden_fields','医生创建研究时须由本人负责',status=400)
    def mutation():
        owner_id=actor.doctor_id if actor.role=='doctor' else data.get('owner_id')
        doctors=validate_doctors(actor,[owner_id] if owner_id else [])
        study=Study.objects.create(tenant_id=actor.tenant_id,owner=doctors[0],**{k:v for k,v in data.items() if k in FIELDS})
        StudyMember.objects.create(tenant_id=actor.tenant_id,study=study,doctor=doctors[0]);audit(actor,'create','study',study.id,{'name':study.name,'code':study.code});return study
    return mutate_with_quota(actor,'studies',mutation)

def update_study(actor,study_id,data,expected_revision):
    require_tenant(actor)
    if set(data)-FIELDS-{'owner_id'}:raise ApiError('forbidden_fields','包含不可修改的字段',status=400)
    def mutation():
        study=get_object(editable_studies(actor),study_id,True);ensure_revision(study,expected_revision)
        if study.state=='ended':raise ApiError('study_ended','已结束研究只允许查看和导出')
        validate_dates(data,study)
        if 'owner_id' in data:
            require_role(actor,'tenant_admin');owner=validate_doctors(actor,[data['owner_id']])[0];study.owner=owner
            StudyMember.objects.get_or_create(tenant_id=actor.tenant_id,study=study,doctor=owner)
        for k,v in data.items():
            if k in FIELDS:setattr(study,k,v)
        study.revision+=1;study.save();audit(actor,'update','study',study.id,{k:str(v) if v is not None else None for k,v in data.items()});return study
    return mutate_with_quota(actor,'studies',mutation,delta=0)

def set_study_members(actor,study_id,doctor_ids,expected_revision):
    require_tenant(actor)
    def mutation():
        study=get_object(editable_studies(actor),study_id,True);ensure_revision(study,expected_revision)
        if study.state=='ended':raise ApiError('study_ended','已结束研究不能修改成员')
        doctors=validate_doctors(actor,[*doctor_ids,study.owner_id]);ids={d.id for d in doctors}
        from apps.followups.models import Enrollment
        from apps.followups.selectors import ACTIVE_STATES
        if Enrollment.objects.filter(study=study,state__in=ACTIVE_STATES).exclude(doctor_id__in=ids).exists():
            raise ApiError('followup_transfer_required','请先转交该成员尚未结束的随访职责')
        StudyMember.objects.filter(study=study).exclude(doctor_id__in=ids).delete()
        for d in doctors:StudyMember.objects.get_or_create(tenant_id=actor.tenant_id,study=study,doctor=d)
        study.revision+=1;study.save();audit(actor,'members','study',study.id,{'doctor_ids':[str(i) for i in ids]});return study
    return mutate_with_quota(actor,'studies',mutation,delta=0)

def validate_protocol(actor,stages):
    if not isinstance(stages,list) or not 1<=len(stages)<=100:raise ApiError('invalid_protocol','研究需要配置 1 至 100 个访视阶段')
    kinds=[s.get('kind') if isinstance(s,dict) else None for s in stages]
    if kinds.count('baseline')!=1 or kinds.count('screening')>1 or kinds.count('end')>1 or any(k not in ['screening','baseline','followup','end'] for k in kinds):raise ApiError('invalid_protocol','必须且只能设置一次基线期，筛选期和结束期各至多一次')
    if ('screening' in kinds and kinds[0]!='screening') or ('end' in kinds and kinds[-1]!='end') or kinds.index('baseline')!=(1 if kinds[0]=='screening' else 0):raise ApiError('invalid_protocol','筛选期须在首位，随后为基线期，结束期须在末位')
    required=False;previous=0;version_ids=[]
    for s in stages:
        if set(s)-{'name','kind','offset_days','window_before','window_after','bindings'}:raise ApiError('invalid_protocol','阶段包含未知配置')
        if not isinstance(s.get('name'),str) or not s['name'].strip() or len(s['name'])>200:raise ApiError('invalid_protocol','请填写有效阶段名称')
        for field in ['offset_days','window_before','window_after']:
            value=s.get(field,0)
            if type(value)!=int or not 0<=value<=36500:raise ApiError('invalid_protocol','日期偏移和窗口须为非负整数')
        offset=s.get('offset_days',0)
        if s['kind'] in ['screening','baseline'] and offset!=0:raise ApiError('invalid_protocol','筛选期及基线期的偏移须为零')
        if offset<previous:raise ApiError('invalid_protocol','后续日期偏移不能递减')
        previous=offset;bindings=s.get('bindings',[])
        if not isinstance(bindings,list) or len(bindings)>100:raise ApiError('invalid_protocol','阶段表单配置无效')
        seen=set()
        for b in bindings:
            if not isinstance(b,dict) or set(b)!={'form_version_id','respondent','required'} or b['respondent'] not in ['doctor','patient'] or type(b['required'])!=bool:raise ApiError('invalid_protocol','表单绑定须指定版本、填写对象和必需状态')
            pair=(str(b['form_version_id']),b['respondent'])
            if pair in seen:raise ApiError('invalid_protocol','同一阶段不能重复绑定同版本同填写对象')
            seen.add(pair);version_ids.append(pair[0]);required=required or b['required']
    if not required:raise ApiError('invalid_protocol','研究至少需要一份必需表单')
    from django.core.exceptions import ValidationError
    try:versions=list(FormVersion.objects.filter(tenant_id=actor.tenant_id,id__in=version_ids))
    except (ValidationError,ValueError):raise ApiError('invalid_protocol','表单版本无效')
    if len(versions)!=len(set(version_ids)):raise ApiError('invalid_protocol','请选择本机构已发布表单版本')
    forms=list(Form.objects.filter(id__in={v.form_id for v in versions},deleted_at__isnull=True,paused=False).order_by('id').select_for_update(no_key=True))
    if len(forms)!=len({v.form_id for v in versions}):raise ApiError('invalid_protocol','所用表单已删除或暂停')
    return {str(v.id):v for v in versions}

def protocol_data(study):
    return [{'name':s.name,'kind':s.kind,'offset_days':s.offset_days,'window_before':s.window_before,'window_after':s.window_after,'bindings':[{'form_version_id':str(b.form_version_id),'respondent':b.respondent,'required':b.required} for b in s.bindings.all()]} for s in study.stages.all()]

def save_protocol(actor,study_id,stages,expected_revision):
    require_tenant(actor)
    def mutation():
        study=get_object(editable_studies(actor),study_id,True);ensure_revision(study,expected_revision)
        if study.protocol_frozen or study.state=='ended':raise ApiError('protocol_frozen','生成首位受试者后访视流程固定')
        versions=validate_protocol(actor,stages)
        FormBinding.objects.filter(stage__study=study).delete();VisitDefinition.objects.filter(study=study).delete()
        for position,data in enumerate(stages):
            stage=VisitDefinition.objects.create(tenant_id=actor.tenant_id,study=study,position=position,**{k:data[k] for k in ['name','kind','offset_days','window_before','window_after'] if k in data})
            FormBinding.objects.bulk_create([FormBinding(tenant_id=actor.tenant_id,stage=stage,form_version=versions[str(b['form_version_id'])],respondent=b['respondent'],required=b['required']) for b in data.get('bindings',[])])
        study.revision+=1;study.save();audit(actor,'protocol','study',study.id,{'stage_count':len(stages)});return study
    return mutate_with_quota(actor,'studies',mutation,delta=0)

def set_study_state(actor,study_id,state,expected_revision):
    require_tenant(actor)
    def mutation():
        study=get_object(editable_studies(actor),study_id,True);ensure_revision(study,expected_revision)
        transitions={'draft':{'active'},'active':{'paused','ended'},'paused':{'active','ended'},'ended':set()}
        if state not in transitions[study.state]:raise ApiError('invalid_state','当前研究不能执行该状态变更')
        if state=='active':
            validate_doctors(actor,[study.owner_id]);validate_protocol(actor,protocol_data(study))
        if state=='ended':
            from apps.followups.models import Enrollment
            from apps.followups.selectors import ACTIVE_STATES
            if Enrollment.objects.filter(study=study,state__in=ACTIVE_STATES).exists():
                raise ApiError('study_has_followups','请先完成或停止全部受试者随访')
        study.state=state;study.revision+=1;study.save();audit(actor,'state','study',study.id,{'state':state});return study
    return mutate_with_quota(actor,'studies',mutation,delta=0)

def delete_study(actor,study_id,expected_revision):
    require_tenant(actor)
    def mutation():
        study=get_object(editable_studies(actor),study_id,True);ensure_revision(study,expected_revision)
        if study.state not in ['draft','ended']:raise ApiError('study_not_ended','请先结束研究再删除')
        study.deleted_at=timezone.now();study.revision+=1;study.save();audit(actor,'delete','study',study.id,{});return study
    return mutate_with_quota(actor,'studies',mutation,delta=-1)

def restore_study(actor,study_id,expected_revision):
    require_tenant(actor);require_role(actor,'tenant_admin')
    def mutation():
        study=get_object(editable_studies(actor,True).filter(deleted_at__isnull=False),study_id,True);ensure_revision(study,expected_revision)
        study.deleted_at=None;study.revision+=1;study.save();audit(actor,'restore','study',study.id,{});return study
    return mutate_with_quota(actor,'studies',mutation)
