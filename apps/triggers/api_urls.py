# apps/triggers/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('recent/',            api_views.recent_events, name='api_trigger_recent'),
    path('zone/<int:zone_id>/', api_views.zone_events,  name='api_trigger_zone'),
    path('fire/',              api_views.fire_trigger,  name='api_trigger_fire'),
]
