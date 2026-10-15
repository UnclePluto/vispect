"""开发 Web 进程只保留运行凭据；结构迁移和演示升级在独立进程执行。"""
import os,sys
from pathlib import Path
for key in ['MIGRATION_DATABASE_URL','VISPECT_OWNER_PASSWORD','VISPECT_MANAGEMENT','POSTGRES_PASSWORD','DEMO_PASSWORD']:
    os.environ.pop(key,None)
os.execv(sys.executable,[sys.executable,str(Path(__file__).resolve().parents[1]/'backend/manage.py'),'runserver','127.0.0.1:8000','--noreload'])
