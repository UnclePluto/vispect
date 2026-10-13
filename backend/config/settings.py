import os
import sys
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "django.contrib.sessions", "rest_framework", "apps.core", "apps.tenants", "apps.accounts", "apps.doctors", "apps.patients", "apps.forms", "apps.studies"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "apps.core.middleware.TenantContextMiddleware"]
DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=0), "control": dj_database_url.parse(os.environ["CONTROL_DATABASE_URL"], conn_max_age=0)}
if os.environ.get("VISPECT_MANAGEMENT") == "1" or "pytest" in sys.modules:
    DATABASES["migration"] = dj_database_url.parse(os.environ["MIGRATION_DATABASE_URL"])
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
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
