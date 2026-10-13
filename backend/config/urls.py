from django.urls import path
from apps.core.health import health
urlpatterns = [path('api/health/', health)]
