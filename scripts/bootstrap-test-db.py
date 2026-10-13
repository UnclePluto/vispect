"""独立测试库准备；只由迁移账号运行，不用于 Web 请求。"""
import os
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

def provision_test_database(owner_dsn: str, app_dsn: str, control_dsn: str) -> None:
    info = conninfo_to_dict(owner_dsn)
    database = info['dbname']
    if not database.endswith('_test'):
        raise ValueError('测试库名称必须以 _test 结尾')
    with psycopg.connect(make_conninfo(owner_dsn, dbname='postgres'), autocommit=True) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', [database]).fetchone():
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    with psycopg.connect(owner_dsn, autocommit=True) as conn:
        conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        for dsn in [app_dsn,control_dsn]:
            role = conninfo_to_dict(dsn)['user']
            conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))

if __name__ == '__main__':
    dsns = [make_conninfo(os.environ[key], dbname='vispect_test') for key in ['MIGRATION_DATABASE_URL','DATABASE_URL','CONTROL_DATABASE_URL']]
    provision_test_database(*dsns)
    print('独立 PostgreSQL 测试库已准备。')
