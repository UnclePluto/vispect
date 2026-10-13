from django.db.models import F
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.context import current_actor
from apps.patients.selectors import visible_patients
from apps.studies.selectors import visible_studies
from apps.followups.selectors import visible_visits
from apps.followups.schedule import local_today
from apps.followups.calendar import calendar_payload
class DashboardView(APIView):
    def get(self,request):
        actor=current_actor(request);today=local_today()
        tasks=visible_visits(actor).filter(status='pending',id=F('enrollment__current_visit_id'),enrollment__state__in=['screening','following'],study__state='active')
        return Response({'patients':visible_patients(actor).count(),'studies':visible_studies(actor).count(),'today_tasks':tasks.filter(planned_on=today).count(),'overdue_tasks':tasks.filter(window_end__lt=today).count(),'tasks':[calendar_payload(v) for v in tasks.select_related('enrollment__study','enrollment__patient','enrollment__doctor','stage')[:10]]})
