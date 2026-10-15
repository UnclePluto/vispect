"""只重建固定的 vispect_e2e_test 验收库，然后启动真实 Django 服务。"""
import os,sys,importlib.util
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
for key in ['DATABASE_URL','CONTROL_DATABASE_URL','MIGRATION_DATABASE_URL']:
    os.environ[key]=urlunsplit(urlsplit(os.environ[key])._replace(path='/vispect_e2e_test'))
os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',VISPECT_MANAGEMENT='1',DJANGO_DEBUG='true',DJANGO_COOKIE_SECURE='false',SESSION_COOKIE_NAME='vispect_e2e_session',CSRF_COOKIE_NAME='vispect_e2e_csrf',DEMO_PASSWORD=os.environ.get('E2E_DEMO_PASSWORD','E2e-Demo-Strong-Password-2026!'))
spec=importlib.util.spec_from_file_location('bootstrap',ROOT/'scripts/bootstrap-test-db.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.provision_test_database(os.environ['MIGRATION_DATABASE_URL'],os.environ['DATABASE_URL'],os.environ['CONTROL_DATABASE_URL'])
import django;django.setup()
from django.core.management import call_command,execute_from_command_line
call_command('migrate',database='migration',interactive=False,verbosity=0)
with psycopg.connect(os.environ['MIGRATION_DATABASE_URL'],autocommit=True) as conn:
    assert conn.info.dbname=='vispect_e2e_test'
    tables=[r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'") if r[0]=='django_session' or r[0].startswith(('tenants_','accounts_','core_','doctors_','patients_','forms_','studies_','followups_'))]
    if tables:conn.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier,tables))))
call_command('seed_demo',verbosity=0)
from django.db import connections
connections['migration'].close();del connections['migration'];del connections.databases['migration']
for key in ['MIGRATION_DATABASE_URL','VISPECT_OWNER_PASSWORD','VISPECT_MANAGEMENT','POSTGRES_PASSWORD','DEMO_PASSWORD']:
    os.environ.pop(key,None)
execute_from_command_line(['manage.py','runserver','127.0.0.1:8001','--noreload'])
