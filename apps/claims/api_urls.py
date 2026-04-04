# apps/claims/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('',          api_views.list_claims,       name='api_list_claims'),
    path('<int:pk>/', api_views.claim_detail_api,  name='api_claim_detail'),
]
