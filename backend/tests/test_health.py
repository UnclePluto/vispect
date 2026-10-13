import subprocess
import os
import sys
from pathlib import Path
import psycopg

def test_health_reports_postgresql(client):
    response = client.get('/api/health/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'postgresql'}

def test_health_hides_unavailable_database_details():
    env = dict(os.environ, DATABASE_URL='postgresql://invalid:secret@127.0.0.1:1/secret_database?connect_timeout=1')
    code = "import django;django.setup();from django.test import Client;r=Client().get('/api/health/');assert r.status_code==503;assert b'secret' not in r.content"
    result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

def test_runtime_roles_cannot_bypass_rls():
    for key in ['DATABASE_URL', 'CONTROL_DATABASE_URL']:
        with psycopg.connect(os.environ[key]) as conn:
            row = conn.execute('SELECT rolsuper, rolbypassrls, rolcreatedb FROM pg_roles WHERE rolname=current_user').fetchone()
            assert row == (False, False, False)
