# apps/workers/urls.py
from django.urls import path
from . import views

app_name = 'workers'

urlpatterns = [
    path('dashboard/',                       views.dashboard,          name='dashboard'),
    path('dashboard/simulate-trigger/',      views.simulate_trigger,   name='simulate_trigger'),
    path('account/',                         views.account,            name='account'),
    path('kyc/submit/',                      views.kyc_submit,         name='kyc_submit'),
]
