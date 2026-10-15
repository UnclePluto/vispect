import os
import uuid
from contextlib import contextmanager
import psycopg
from psycopg import sql
from django.db import connections,transaction
from rest_framework.test import APIClient
from apps.tenants.models import Tenant,TenantQuota
from apps.accounts.models import Account
from apps.core.types import Actor

class TestWorld:
    __test__=False
    password='World-Strong-Password-2026!'
    def __init__(self,create_identities=True):
        self.app_dsn=os.environ['DATABASE_URL']
        self.control_dsn=os.environ['CONTROL_DATABASE_URL']
        self.tenants={slug:Tenant.objects.using('migration').create(slug=slug,name=f'测试机构 {slug}') for slug in ['a','b']}
        for tenant in self.tenants.values():
            self.owner_save(TenantQuota(tenant=tenant))
        self.accounts={}
        for slug in ['a','b']:
            for role,username in [('tenant_admin','admin'),('doctor','doctor')]:
                account=Account(tenant=self.tenants[slug],username=username,name=f'测试{username}',role=role)
                account.set_password(self.password)
                if create_identities:self.bind_identity(account,self.phone_for(slug,role))
                else:self.owner_save(account)
                if role=='doctor':
                    from apps.doctors.models import Doctor
                    doctor=Doctor(tenant=self.tenants[slug],account=account,name=account.name)
                    self.owner_save(doctor);account.doctor_id=doctor.id;self.owner_save(account)
                self.accounts[slug,role]=account
        account=Account(username='platform',name='平台管理员',role='platform_admin')
        account.set_password(self.password)
        if create_identities:self.bind_identity(account,self.phone_for(None,'platform_admin'))
        else:self.owner_save(account)
        self.accounts[None,'platform_admin']=account

    def owner_save(self,instance):
        with self.owner_context(getattr(instance,'tenant_id',None)):
            instance.save(using='migration')

    @contextmanager
    def owner_context(self,tenant_id):
        with transaction.atomic(using='migration'):
            with connections['migration'].cursor() as cur:cur.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(tenant_id) if tenant_id else ''])
            yield

    def actor(self,tenant,role):
        account=self.accounts[tenant,role]
        return Actor(account.id,account.tenant_id,account.role,account.doctor_id)

    def post(self,client,path,data,**extra):
        token=client.get('/api/auth/csrf/').json()['csrf_token']
        return client.post(path,data,format='json',HTTP_X_CSRFTOKEN=token,**extra)

    def login(self,tenant,role,enforce_csrf=True,unified=False):
        client=APIClient(enforce_csrf_checks=enforce_csrf)
        account=self.accounts[tenant,role]
        if unified:
            phone=self.phone_for(tenant,role)
            if account.identity_id is None:self.bind_identity(account,phone)
            else:
                from apps.accounts.models import LoginIdentity
                phone=LoginIdentity.objects.using('migration').get(id=account.identity_id).phone
            response=self.post(client,'/api/auth/login/',{'phone':phone,'password':self.password})
            assert response.status_code==200,response.content
            data=response.json()
            if data['next']=='choose_workspace':
                response=self.post(client,'/api/auth/switch-workspace/',{'account_id':str(account.id),'workspace_token':data['workspace_token']})
                assert response.status_code==200,response.content
                data=response.json()
            client.defaults['HTTP_X_WORKSPACE_TOKEN']=data['workspace_token']
            return client
        path='/api/auth/platform-login/' if tenant is None else '/api/auth/tenant-login/'
        data={'username':account.username,'password':self.password}
        if tenant is not None:data['tenant']=tenant
        response=self.post(client,path,data)
        assert response.status_code==200,response.content
        return client

    def runtime_rows(self,tenant,table):
        with psycopg.connect(self.app_dsn) as conn:
            conn.execute("SELECT set_config('vispect.tenant_id',%s,true)",[str(self.tenants[tenant].id)])
            return sorted(row[0] for row in conn.execute(sql.SQL('SELECT id FROM {}').format(sql.Identifier(table))))

    def account_ids(self,tenant):
        return sorted(a.id for (slug,_),a in self.accounts.items() if slug==tenant)

    def doctor(self,tenant,**data):
        from apps.doctors.services import create_doctor
        doctor=create_doctor(self.actor(tenant,'tenant_admin'),{'username':f'doctor-{uuid.uuid4().hex[:8]}','name':'新增测试医生','password':self.password,**data})
        doctor.account.must_change_password=False;self.owner_save(doctor.account)
        return doctor

    def patient(self,tenant,**data):
        from apps.patients.services import create_patient
        return create_patient(self.actor(tenant,'tenant_admin'),{'code':uuid.uuid4().hex[:10],'name':'测试患者','doctor_ids':[self.accounts[tenant,'doctor'].doctor_id],**data})

    def form_version(self,tenant,definition=None):
        from apps.forms.services import create_form,publish_form
        actor=self.actor(tenant,'tenant_admin')
        form=create_form(actor,definition or {'protocol_version':1,'title':'测试表单','questions':[{'id':'q1','type':'text','title':'测试题目','required':True}]})
        return publish_form(actor,form.id,form.revision,uuid.uuid4().hex)

    def study(self,tenant,screening=False,definition=None):
        from apps.studies.services import create_study,save_protocol,set_study_state
        actor=self.actor(tenant,'doctor');version=self.form_version(tenant,definition)
        s=create_study(actor,{'name':'测试研究','code':uuid.uuid4().hex[:10]})
        def stage(kind,offset):return {'name':kind,'kind':kind,'offset_days':offset,'window_before':0,'window_after':3,'bindings':[{'form_version_id':str(version.id),'respondent':'patient','required':True}]}
        stages=([stage('screening',0)] if screening else [])+[stage('baseline',0),stage('followup',30)]
        s=save_protocol(actor,s.id,stages,s.revision)
        return set_study_state(actor,s.id,'active',s.revision)

    def entry(self,tenant,definition=None):
        from apps.followups.enrollments import add_subject,confirm_enrollment
        from apps.core.context import tenant_transaction
        a=self.actor(tenant,'doctor');s=self.study(tenant,definition=definition);p=self.patient(tenant)
        e=add_subject(a,s.id,p.id,a.doctor_id,uuid.uuid4().hex[:8],uuid.uuid4().hex)
        e=confirm_enrollment(a,e.id,uuid.uuid4().hex[:8],e.added_on,uuid.uuid4().hex)
        with tenant_transaction(a.tenant_id):
            v=e.current_visit;b=v.stage.bindings.select_related('form_version__form').first()
        return e,v,b

    def bind_identity(self,account,phone,password=None):
        from apps.accounts.models import LoginIdentity
        from apps.accounts.phone import normalize_phone
        identity=LoginIdentity.objects.using('migration').filter(phone=normalize_phone(phone)).first()
        if identity is None:
            identity=LoginIdentity(phone=normalize_phone(phone),name=account.name,must_change_password=False)
            if password is None and account.has_usable_password():identity.password=account.password
            else:identity.set_password(password or self.password)
            identity.save(using='migration')
        account.identity=identity;self.owner_save(account)
        return identity

    def phone_for(self,tenant,role):
        keys=[('a','tenant_admin'),('a','doctor'),('b','tenant_admin'),('b','doctor'),(None,'platform_admin')]
        return f'139000020{keys.index((tenant,role))+1:02d}'
