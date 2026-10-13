"""新建本地配置；已有文件绝不覆盖，生成值不输出到终端。"""
from pathlib import Path
import secrets
from urllib.parse import quote
root=Path(__file__).resolve().parents[1];target=root/'.env'
if target.exists():
    print('已有 .env，保留现有配置。')
else:
    values={'DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'DJANGO_DEBUG':'true','DJANGO_COOKIE_SECURE':'false','ALLOWED_HOSTS':'localhost,127.0.0.1,testserver','DATABASE_PORT':'55432','POSTGRES_PASSWORD':secrets.token_urlsafe(32),'VISPECT_OWNER_PASSWORD':secrets.token_urlsafe(32),'VISPECT_APP_PASSWORD':secrets.token_urlsafe(32),'VISPECT_CONTROL_PASSWORD':secrets.token_urlsafe(32),'DEMO_PASSWORD':secrets.token_urlsafe(24)}
    for key,role,password in [('DATABASE_URL','vispect_app','VISPECT_APP_PASSWORD'),('CONTROL_DATABASE_URL','vispect_control','VISPECT_CONTROL_PASSWORD'),('MIGRATION_DATABASE_URL','vispect_owner','VISPECT_OWNER_PASSWORD')]:values[key]=f"postgresql://{role}:{quote(values[password],safe='')}@127.0.0.1:55432/vispect"
    target.write_text(''.join(f'{key}={value}\n' for key,value in values.items()));target.chmod(0o600);print('已创建 .env，权限 600；密码未输出。')
