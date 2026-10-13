import os
import sys
from pathlib import Path
import dj_database_url
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "django.contrib.sessions", "rest_framework", "apps.core", "apps.tenants", "apps.accounts", "apps.doctors", "apps.patients", "apps.forms", "apps.studies", "apps.followups"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "apps.core.middleware.TenantContextMiddleware"]
def database_url(key,role,password_key):
    if os.environ.get(key):return os.environ[key]
    password=quote(os.environ[password_key],safe='')
    host=os.environ.get('VISPECT_DATABASE_HOST','127.0.0.1');port=os.environ.get('VISPECT_DATABASE_PORT','5432');name=quote(os.environ.get('VISPECT_DATABASE_NAME','vispect'),safe='')
    return f'postgresql://{role}:{password}@{host}:{port}/{name}'
DATABASES = {"default": dj_database_url.parse(database_url('DATABASE_URL','vispect_app','VISPECT_APP_PASSWORD'), conn_max_age=0), "control": dj_database_url.parse(database_url('CONTROL_DATABASE_URL','vispect_control','VISPECT_CONTROL_PASSWORD'), conn_max_age=0)}
if os.environ.get("VISPECT_MANAGEMENT") == "1" or "pytest" in sys.modules:
    DATABASES["migration"] = dj_database_url.parse(database_url('MIGRATION_DATABASE_URL','vispect_owner','VISPECT_OWNER_PASSWORD'))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_COOKIE_SECURE',str(not DEBUG)).lower()=='true'
SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME','sessionid')
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_NAME = os.environ.get('CSRF_COOKIE_NAME','csrftoken')
CSRF_TRUSTED_ORIGINS = [value for value in os.environ.get('CSRF_TRUSTED_ORIGINS','').split(',') if value]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
AUTH_USER_MODEL = 'accounts.Account'
DATABASE_ROUTERS = ['apps.core.db_router.SessionRouter']
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':['apps.accounts.authentication.SessionActorAuthentication'],
    'DEFAULT_PERMISSION_CLASSES':['apps.core.permissions.ActorPermission'],
    'UNAUTHENTICATED_USER':None,
    'EXCEPTION_HANDLER':'apps.core.errors.exception_handler',
}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
