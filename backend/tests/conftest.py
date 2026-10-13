import pytest
import os
import subprocess
import sys
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
import psycopg
from psycopg import sql

@pytest.fixture(scope='session',autouse=True)
def prepare_test_database(django_db_blocker):
    from django.db import connections
    backend=Path(__file__).resolve().parents[1]
    for key in ['DATABASE_URL','CONTROL_DATABASE_URL','MIGRATION_DATABASE_URL']:
        parts=urlsplit(os.environ[key])
        os.environ[key]=urlunsplit(parts._replace(path='/vispect_test'))
    for alias in connections:
        connections[alias].close()
        connections.databases[alias]['NAME']='vispect_test'
    spec=importlib.util.spec_from_file_location('bootstrap_test_db',backend.parent/'scripts/bootstrap-test-db.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.provision_test_database(os.environ['MIGRATION_DATABASE_URL'],os.environ['DATABASE_URL'],os.environ['CONTROL_DATABASE_URL'])
    with psycopg.connect(os.environ['MIGRATION_DATABASE_URL'],autocommit=True) as conn:
        tables=[r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'") if r[0]=='django_session' or r[0].startswith(('tenants_','accounts_','core_','doctors_','patients_','forms_','studies_','followups_'))]
        if tables:conn.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier,tables))))
    result=subprocess.run([sys.executable,'manage.py','migrate','--database','migration','--noinput'],cwd=backend,env=dict(os.environ,VISPECT_MANAGEMENT='1'),capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    yield
    connections.close_all()

@pytest.fixture(autouse=True)
def runtime_database(django_db_blocker,prepare_test_database):
    with django_db_blocker.unblock():
        yield

@pytest.fixture
def world(runtime_database):
    from django.db import connections
    from tests.world import TestWorld
    connections.close_all()
    with psycopg.connect(os.environ['MIGRATION_DATABASE_URL'],autocommit=True) as conn:
        tables=[r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'") if r[0]=='django_session' or r[0].startswith(('tenants_','accounts_','core_','doctors_','patients_','forms_','studies_','followups_'))]
        if tables:conn.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier,tables))))
    result=TestWorld()
    yield result
    connections.close_all()
