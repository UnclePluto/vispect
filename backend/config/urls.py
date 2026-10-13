from django.urls import path
from apps.core.health import health
from apps.accounts.api import CsrfView,TenantLoginView,PlatformLoginView,MeView,LogoutView,ChangePasswordView
from apps.tenants.api import TenantsView,TenantDetailView,AdministratorView,PlatformUsageView
from apps.doctors.api import DoctorsView,DoctorDetailView,DoctorRestoreView,DoctorEnabledView,DoctorOptionsView
urlpatterns = [path('api/health/', health)] + [path(f'api/auth/{name}/',view.as_view()) for name,view in [('csrf',CsrfView),('tenant-login',TenantLoginView),('platform-login',PlatformLoginView),('me',MeView),('logout',LogoutView),('change-password',ChangePasswordView)]]
urlpatterns += [path('api/platform/tenants/',TenantsView.as_view()),path('api/platform/tenants/<uuid:tenant_id>/',TenantDetailView.as_view()),path('api/platform/tenants/<uuid:tenant_id>/administrator/',AdministratorView.as_view()),path('api/platform/usage/',PlatformUsageView.as_view())]
urlpatterns += [path('api/doctors/',DoctorsView.as_view()),path('api/doctors/options/',DoctorOptionsView.as_view()),path('api/doctors/<uuid:doctor_id>/',DoctorDetailView.as_view()),path('api/doctors/<uuid:doctor_id>/restore/',DoctorRestoreView.as_view()),path('api/doctors/<uuid:doctor_id>/enabled/',DoctorEnabledView.as_view())]

from apps.patients.api import PatientsView,PatientDetailView,PatientAssignView,PatientRestoreView
urlpatterns += [path('api/patients/',PatientsView.as_view()),path('api/patients/<uuid:patient_id>/',PatientDetailView.as_view()),path('api/patients/<uuid:patient_id>/assign-doctors/',PatientAssignView.as_view()),path('api/patients/<uuid:patient_id>/restore/',PatientRestoreView.as_view())]
