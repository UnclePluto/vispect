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
    def __init__(self):
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
                self.owner_save(account)
                if role=='doctor':
                    from apps.doctors.models import Doctor
                    doctor=Doctor(tenant=self.tenants[slug],account=account,name=account.name)
                    self.owner_save(doctor);account.doctor_id=doctor.id;self.owner_save(account)
                self.accounts[slug,role]=account
        account=Account(username='platform',name='平台管理员',role='platform_admin')
        account.set_password(self.password);self.owner_save(account)
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

    def login(self,tenant,role,enforce_csrf=True):
        client=APIClient(enforce_csrf_checks=enforce_csrf)
        account=self.accounts[tenant,role]
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
