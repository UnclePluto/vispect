import os,uuid,copy
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from apps.accounts.models import Account,LoginIdentity
from apps.core.context import tenant_transaction
from apps.core.types import Actor
from apps.core.models import AuditEvent
from apps.core.audit import audit
from apps.tenants.models import Tenant
from apps.tenants.services import create_tenant,validate_initial_password
from apps.doctors.services import create_doctor
from apps.doctors.models import Doctor
from apps.patients.services import create_patient,delete_patient
from apps.patients.models import Patient
from apps.forms.services import create_form,publish_form,save_draft,delete_form
from apps.forms.models import Form
from apps.studies.services import create_study,save_protocol,set_study_members,set_study_state,delete_study
from apps.studies.models import Study
from apps.followups.enrollments import add_subject,confirm_enrollment
from apps.followups.answers import submit_answer,revise_answer
from apps.followups.transitions import complete_visit,stop_followup
from apps.followups.exports import export_answers
from apps.followups.schedule import local_today

SURVEY={'protocol_version':1,'title':'生活方式记录表','description':'虚构演示数据，用于体验表单和研究流程。','questions':[
    {'id':'condition','type':'radio','title':'本次是否需要记录身体状况变化','required':True,'options':[{'id':'yes','label':'是'},{'id':'no','label':'否'}],'jumps':{'no':'habits'}},
    {'id':'notes','type':'text','title':'状况说明','required':True,'condition':{'mode':'all','rules':[{'question_id':'condition','operator':'eq','value':'yes'}]}},
    {'id':'minutes','type':'number','title':'每日运动分钟数','min':0,'max':300,'precision':0},
    {'id':'habits','type':'checkbox','title':'本周活动','options':[{'id':'walk','label':'散步'},{'id':'read','label':'阅读'},{'id':'exercise','label':'运动'}]},
    {'id':'recorded_on','type':'date','title':'记录日期'},
    {'id':'sleep','type':'select','title':'作息情况','options':[{'id':'regular','label':'规律'},{'id':'irregular','label':'不规律'}]},
    {'id':'energy','type':'slider','title':'主观精力记录','min':0,'max':10,'step':1},
    {'id':'comment','type':'textarea','title':'其他备注','max_length':2000},
]}
CLINICIAN={'protocol_version':1,'title':'医生随访记录表','questions':[{'id':'memo','type':'textarea','title':'本次随访记录','required':True},{'id':'recorded_on','type':'date','title':'记录日期'}]}

class Command(BaseCommand):
    help='通过业务服务初始化两个虚构演示机构；初始密码从 DEMO_PASSWORD 读取。'
    def handle(self,*args,**options):
        password=os.environ.get('DEMO_PASSWORD')
        if not password:raise CommandError('请设置 DEMO_PASSWORD，至少 12 位，不会打印密码。')
        try:validate_initial_password(password)
        except Exception as exc:raise CommandError('DEMO_PASSWORD 不符合密码强度要求') from exc
        with transaction.atomic(using='control'):
            platform=Account.objects.using('control').filter(tenant_id=None,username='platform').first()
            if platform is None:
                identity=LoginIdentity.objects.using('control').filter(phone='+8619900001000').first()
                if identity is None:
                    identity=LoginIdentity(phone='+8619900001000',name='平台管理员');identity.set_password(password);identity.save(using='control')
                platform=Account(username='platform',identity=identity,name='平台管理员',role='platform_admin');platform.set_unusable_password();platform.save(using='control')
                audit(Actor(platform.id,None,'platform_admin',None),'bootstrap_platform','account',platform.id,{'username':'platform'})
        if platform.identity_id is None:raise CommandError('旧演示账号尚未映射手机号，请先运行 upgrade-demo-identities.py 预检并应用。')
        platform_actor=Actor(platform.id,None,'platform_admin',None)
        for slug,label in [('demo-a','示例健康机构 A'),('demo-b','示例健康机构 B')]:
            tenant=Tenant.objects.using('control').filter(slug=slug).first()
            created=tenant is None
            if created:tenant=create_tenant(platform_actor,{'slug':slug,'name':label,'admin_phone':'19900001001' if slug=='demo-a' else '19900001002','admin_initial_password':password})
            admin=Account.objects.using('control').filter(tenant=tenant,role='tenant_admin',is_active=True).first()
            if admin is None:raise CommandError(f'{slug} 没有可用机构管理员，未修改现有数据。')
            if admin.identity_id is None:raise CommandError('旧机构管理员尚未映射手机号，请先运行演示身份升级。')
            if created:admin.username='admin';admin.save(using='control',update_fields=['username'])
            actor=Actor(admin.id,tenant.id,'tenant_admin',None)
            with tenant_transaction(tenant.id):
                if AuditEvent.objects.filter(action='seed_demo_complete',object_id=tenant.id).exists():
                    self.stdout.write(f'{slug} 已初始化，保留现有修改。');continue
                if any(model.objects.exists() for model in [Doctor,Patient,Form,Study]):raise CommandError(f'{slug} 已有非本次初始化的数据，拒绝覆盖或混入演示记录。')
                self.seed_tenant(actor,password)
                audit(actor,'seed_demo_complete','tenant',tenant.id,{'version':1,'synthetic':True})
            self.stdout.write(f'{slug} 初始化完成；使用演示手机号登录，密码来自 DEMO_PASSWORD。')
        self.stdout.write('演示手机号为虚构测试标识，未验证、不发送短信；所有新身份首次登录必须修改密码。')

    def seed_tenant(self,actor,password):
        slug=Tenant.objects.using('control').get(id=actor.tenant_id).slug
        phones=['19900001003','19900001004'] if slug=='demo-a' else ['19900001001','19900001005']
        doctors=[]
        for i,phone in enumerate(phones,1):
            doctor=create_doctor(actor,{'name':f'示例医生{i}','login_phone':phone,'initial_password':password,'organization':'示例机构','department':'健康管理','title':'研究成员'})
            doctor.account.username=f'doctor{i}';doctor.account.save(update_fields=['username']);doctors.append(doctor)
        patients=[create_patient(actor,{'name':f'示例患者{name}','code':f'{i:06d}','gender':'unknown','phone':'虚构联系方式','notes':'此档案为虚构演示资料。','doctor_ids':[doctors[i-1].id] if i<=2 else [d.id for d in doctors]}) for i,name in enumerate(['甲','乙','丙'],1)]
        survey=create_form(actor,copy.deepcopy(SURVEY));survey_v1=publish_form(actor,survey.id,survey.revision,uuid.uuid4().hex)
        updated=copy.deepcopy(SURVEY);updated['questions'][1]['title']='本次状况变化说明';survey=save_draft(actor,survey.id,updated,2);publish_form(actor,survey.id,survey.revision,uuid.uuid4().hex)
        clinician=create_form(actor,copy.deepcopy(CLINICIAN));clinician_v1=publish_form(actor,clinician.id,clinician.revision,uuid.uuid4().hex)
        def stage(kind,offset,name):return {'name':name,'kind':kind,'offset_days':offset,'window_before':2 if offset else 0,'window_after':3,'bindings':[{'form_version_id':str(survey_v1.id),'respondent':'patient','required':True},{'form_version_id':str(clinician_v1.id),'respondent':'doctor','required':True}]}
        direct=create_study(actor,{'name':'生活方式观察研究','code':'DEMO-DIRECT','owner_id':doctors[0].id,'organization':'示例机构','description':'无筛选期，直接确认入组；两名医生分别负责不同患者。'})
        direct=set_study_members(actor,direct.id,[d.id for d in doctors],direct.revision);direct=save_protocol(actor,direct.id,[stage('baseline',0,'基线期'),stage('followup',30,'30 天随访')],direct.revision);direct=set_study_state(actor,direct.id,'active',direct.revision)
        entries=[]
        for i,patient in enumerate(patients[:2]):
            e=add_subject(actor,direct.id,patient.id,doctors[i].id,f'OBS-{i+1:04d}',uuid.uuid4().hex);e=confirm_enrollment(actor,e.id,f'ENR-{i+1:04d}',local_today(),uuid.uuid4().hex);entries.append(e)
        second=entries[1];visit=second.current_visit
        answer=None
        for binding in visit.stage.bindings.select_related('form_version').all():
            values={'condition':'yes','notes':'示例状况记录','minutes':0,'habits':['walk'],'recorded_on':local_today().isoformat(),'sleep':'regular','energy':5} if binding.respondent=='patient' else {'memo':'示例随访记录'}
            saved=submit_answer(actor,visit.id,binding.id,values,uuid.uuid4().hex)
            if binding.respondent=='patient':answer=saved
        revised=dict(answer.answers);revised['notes']='修正后的示例记录';revise_answer(actor,answer.id,revised,'纠正虚构演示记录',answer.revision)
        complete_visit(actor,visit.id,uuid.uuid4().hex);stop_followup(actor,second.id,'other','虚构演示：展示已停止随访的只读记录。',uuid.uuid4().hex);export_answers(actor,study_id=direct.id)
        screening=create_study(actor,{'name':'健康随访筛选研究','code':'DEMO-SCREENING','owner_id':doctors[1].id,'description':'先完成筛选，再确认入组并进入基线期。'})
        screening=set_study_members(actor,screening.id,[d.id for d in doctors],screening.revision);screening=save_protocol(actor,screening.id,[stage('screening',0,'筛选期'),stage('baseline',0,'基线期'),stage('end',60,'结束期')],screening.revision);screening=set_study_state(actor,screening.id,'active',screening.revision)
        add_subject(actor,screening.id,patients[2].id,doctors[1].id,'SCREEN-0001',uuid.uuid4().hex)
        archived=create_patient(actor,{'name':'已回收示例档案','code':'DELETED-DEMO','doctor_ids':[doctors[0].id]});delete_patient(actor,archived.id,archived.revision)
        draft=create_form(actor,{'protocol_version':1,'title':'已回收示例草稿','questions':[]});delete_form(actor,draft.id,draft.revision)
        draft_study=create_study(actor,{'name':'已回收示例研究','code':'DELETED-STUDY','owner_id':doctors[0].id});delete_study(actor,draft_study.id,draft_study.revision)
