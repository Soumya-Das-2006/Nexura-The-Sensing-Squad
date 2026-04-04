# apps/payouts/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('',          api_views.list_payouts,      name='api_list_payouts'),
    path('<int:pk>/', api_views.payout_detail_api,  name='api_payout_detail'),
    path('summary/',  api_views.payout_summary,     name='api_payout_summary'),
]
