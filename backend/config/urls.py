from django.urls import path
from apps.core.health import health
from apps.accounts.api import CsrfView,TenantLoginView,PlatformLoginView,MeView,LogoutView,ChangePasswordView
urlpatterns = [path('api/health/', health)] + [path(f'api/auth/{name}/',view.as_view()) for name,view in [('csrf',CsrfView),('tenant-login',TenantLoginView),('platform-login',PlatformLoginView),('me',MeView),('logout',LogoutView),('change-password',ChangePasswordView)]]
