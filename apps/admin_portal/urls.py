from django.urls import path
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('admin-portal/',                               views.dashboard,        name='dashboard'),
    path('admin-portal/workers/',                       views.workers_list,     name='workers'),
    path('admin-portal/claims/',                        views.claims_list,      name='claims'),
    path('admin-portal/claims/<int:claim_id>/approve/', views.approve_claim,    name='approve_claim'),
    path('admin-portal/claims/<int:claim_id>/reject/',  views.reject_claim,     name='reject_claim'),
    path('admin-portal/payouts/',                       views.payouts_list,     name='payouts'),
    path('admin-portal/triggers/',                      views.triggers_list,    name='triggers'),
    path('admin-portal/fraud/',                         views.fraud_flags_list, name='fraud'),
    path('admin-portal/zones/',                         views.zones_list,       name='zones'),
    path('admin-portal/forecast/',                      views.forecast_overview,name='forecast'),
    path('admin-portal/fire-trigger/',                  views.fire_test_trigger,name='fire_trigger'),
    path('admin-portal/kyc/<int:user_id>/approve/',     views.kyc_approve,      name='kyc_approve'),
    path('admin-portal/kyc/<int:user_id>/reject/',      views.kyc_reject,       name='kyc_reject'),
    path('admin-portal/support/',                       views.support_tickets,  name='support'),
]
