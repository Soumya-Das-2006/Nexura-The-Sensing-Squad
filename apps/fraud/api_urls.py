# apps/fraud/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('flags/<int:claim_pk>/',   api_views.claim_flags,   name='api_fraud_flags'),
    path('status/',                 api_views.model_status,  name='api_fraud_status'),
    path('rescore/<int:claim_pk>/', api_views.rescore_claim, name='api_fraud_rescore'),
]
