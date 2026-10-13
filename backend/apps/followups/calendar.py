from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from apps.core.context import current_actor
from apps.core.pagination import paginate
from .selectors import visible_visits
from .serializers import visit_payload

def calendar_payload(visit):
    data=visit_payload(visit)
    data['color']='blue' if visit.status=='completed' else 'gray' if visit.status=='stopped' else 'red' if data['overdue'] else 'yellow'
    return data
class CalendarView(APIView):
    def get(self,request):
        query=visible_visits(current_actor(request)).select_related('enrollment__study','enrollment__patient','enrollment__doctor','stage')
        for name,field in [('study_id','study_id'),('doctor_id','enrollment__doctor_id')]:
            if request.query_params.get(name):query=query.filter(**{field:serializers.UUIDField().run_validation(request.query_params[name])})
        for name,field in [('from','planned_on__gte'),('to','planned_on__lte')]:
            if request.query_params.get(name):query=query.filter(**{field:serializers.DateField().run_validation(request.query_params[name])})
        return Response(paginate(query,request,calendar_payload))
