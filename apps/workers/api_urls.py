# apps/workers/api_urls.py
from .api_views import risk_score_detail
from django.urls import path
from . import api_views

urlpatterns = [
    path('profile/',   api_views.worker_profile,   name='api_worker_profile'),
    path('stats/',     api_views.worker_stats,      name='api_worker_stats'),
    path('dashboard/', api_views.worker_dashboard,  name='api_worker_dashboard'),
    path('risk-score/', api_views.risk_score_detail, name='api_risk_score_detail'),
]
