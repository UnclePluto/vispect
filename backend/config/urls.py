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

from apps.forms.api import FormsView,FormDetailView,FormVersionsView,FormPublishView,FormStateView,PublishedVersionOptionsView
urlpatterns += [path('api/forms/',FormsView.as_view()),path('api/forms/version-options/',PublishedVersionOptionsView.as_view()),path('api/forms/<uuid:form_id>/',FormDetailView.as_view()),path('api/forms/<uuid:form_id>/versions/',FormVersionsView.as_view()),path('api/forms/<uuid:form_id>/publish/',FormPublishView.as_view())] + [path('api/forms/<uuid:form_id>/'+action+'/',FormStateView.as_view(action=action)) for action in ['pause','resume','restore']]

from apps.studies.api import StudiesView,StudyDetailView,StudyMembersView,StudyProtocolView,StudyStateView
urlpatterns += [path('api/studies/',StudiesView.as_view()),path('api/studies/<uuid:study_id>/',StudyDetailView.as_view()),path('api/studies/<uuid:study_id>/members/',StudyMembersView.as_view()),path('api/studies/<uuid:study_id>/protocol/',StudyProtocolView.as_view())] + [path('api/studies/<uuid:study_id>/'+action+'/',StudyStateView.as_view(state=state)) for action,state in [('start','active'),('resume','active'),('pause','paused'),('end','ended'),('restore','restore')]]

from apps.followups.api import StudySubjectsView,EnrollmentDetailView,EnrollmentConfirmView,EnrollmentTransferView,VisitsView,VisitDetailView
urlpatterns += [path('api/studies/<uuid:study_id>/subjects/',StudySubjectsView.as_view()),path('api/enrollments/<uuid:enrollment_id>/',EnrollmentDetailView.as_view()),path('api/enrollments/<uuid:enrollment_id>/confirm/',EnrollmentConfirmView.as_view()),path('api/enrollments/<uuid:enrollment_id>/transfer/',EnrollmentTransferView.as_view()),path('api/visits/',VisitsView.as_view()),path('api/visits/<uuid:visit_id>/',VisitDetailView.as_view())]
