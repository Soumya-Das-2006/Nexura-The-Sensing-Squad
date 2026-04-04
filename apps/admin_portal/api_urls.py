# apps/admin_portal/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('stats/',                        api_views.admin_stats,         name='api_admin_stats'),
    path('workers/',                      api_views.admin_workers,        name='api_admin_workers'),
    path('claims/<int:claim_id>/approve/', api_views.admin_approve_claim, name='api_admin_approve_claim'),
    path('claims/<int:claim_id>/reject/',  api_views.admin_reject_claim,  name='api_admin_reject_claim'),
]
