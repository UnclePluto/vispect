from django.urls import path
from apps.core.health import health
from apps.accounts.api import CsrfView,MeView,LogoutView,ChangePasswordView
from apps.tenants.api import TenantsView,TenantDetailView,AdministratorView,PlatformUsageView
from apps.doctors.api import DoctorsView,DoctorDetailView,DoctorRestoreView,DoctorEnabledView,DoctorOptionsView
urlpatterns = [path('api/health/', health)] + [path(f'api/auth/{name}/',view.as_view()) for name,view in [('csrf',CsrfView),('me',MeView),('logout',LogoutView),('change-password',ChangePasswordView)]]
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

from apps.followups.api import VisitAnswersView,AnswerDetailView,AnswerReviseView,VisitCompleteView,EnrollmentStopView
urlpatterns += [path('api/visits/<uuid:visit_id>/answers/',VisitAnswersView.as_view()),path('api/visits/<uuid:visit_id>/complete/',VisitCompleteView.as_view()),path('api/answers/<uuid:answer_id>/',AnswerDetailView.as_view()),path('api/answers/<uuid:answer_id>/revise/',AnswerReviseView.as_view()),path('api/enrollments/<uuid:enrollment_id>/stop/',EnrollmentStopView.as_view())]

from apps.followups.api import StudyExportView,AnswerExportView,AnswerRevisionsView
urlpatterns += [path('api/studies/<uuid:study_id>/export/',StudyExportView.as_view()),path('api/answers/<uuid:answer_id>/export/',AnswerExportView.as_view()),path('api/answers/<uuid:answer_id>/revisions/',AnswerRevisionsView.as_view())]

from apps.followups.calendar import CalendarView
from apps.core.dashboard import DashboardView
from apps.followups.api import StudyAnswersView
from apps.forms.api import FormReferencesView
urlpatterns += [path('api/calendar/',CalendarView.as_view()),path('api/dashboard/',DashboardView.as_view()),path('api/studies/<uuid:study_id>/answers/',StudyAnswersView.as_view()),path('api/forms/<uuid:form_id>/references/',FormReferencesView.as_view())]

from apps.core.audit_api import AuditView
from apps.core.recycle_api import RecycleView
urlpatterns += [path('api/audit/',AuditView.as_view()),path('api/platform/audit/',AuditView.as_view(platform=True)),path('api/recycle/',RecycleView.as_view())]

from apps.accounts.auth_api import PhoneLoginView,WorkspacesView
urlpatterns += [path('api/auth/login/',PhoneLoginView.as_view()),path('api/auth/workspaces/',WorkspacesView.as_view())]

from apps.accounts.auth_api import SwitchWorkspaceView
urlpatterns += [path('api/auth/switch-workspace/',SwitchWorkspaceView.as_view())]

from apps.accounts.member_lookup import PhoneStatusView
urlpatterns += [path('api/members/phone-status/',PhoneStatusView.as_view())]

from apps.accounts.platform_api import GlobalAccountsView,GlobalAccountActionView
urlpatterns += [path('api/platform/accounts/',GlobalAccountsView.as_view()),path('api/platform/accounts/<uuid:identity_id>/enabled/',GlobalAccountActionView.as_view()),path('api/platform/accounts/<uuid:identity_id>/reset-password/',GlobalAccountActionView.as_view(reset=True))]

from apps.patient_portal.staff_api import PatientAccessView
urlpatterns += [path('api/patients/<uuid:patient_id>/portal-access/',PatientAccessView.as_view())]
from apps.patient_portal.staff_api import PatientEntryOptionsView,PatientBindingEntryView,PatientEntryActionView
urlpatterns += [path('api/forms/<uuid:form_id>/patient-entry-options/',PatientEntryOptionsView.as_view()),path('api/patient-form-bindings/<uuid:binding_id>/entry/',PatientBindingEntryView.as_view())]+[path('api/patient-form-entries/<uuid:entry_id>/'+action+'/',PatientEntryActionView.as_view(action=action)) for action in ['disable','regenerate']]

from apps.patient_portal.auth_api import PatientCsrfView,PatientEntryResolveView,PatientLoginView,PatientMeView,PatientChangePasswordView,PatientLogoutView
urlpatterns += [path('api/patient/csrf/',PatientCsrfView.as_view()),path('api/patient/entry/resolve/',PatientEntryResolveView.as_view())]+[path('api/patient/auth/'+name+'/',view.as_view()) for name,view in [('login',PatientLoginView),('me',PatientMeView),('change-password',PatientChangePasswordView),('logout',PatientLogoutView)]]
from apps.patient_portal.task_api import PatientTasksResolveView,PatientTaskDetailView
urlpatterns += [path('api/patient/tasks/resolve/',PatientTasksResolveView.as_view()),path('api/patient/entries/<str:token>/patients/<uuid:patient_id>/',PatientTaskDetailView.as_view())]
from apps.patient_portal.task_api import PatientTaskAnswersView
urlpatterns += [path('api/patient/entries/<str:token>/patients/<uuid:patient_id>/answers/',PatientTaskAnswersView.as_view())]
