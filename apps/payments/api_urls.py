# apps/payments/api_urls.py
from django.urls import path
from . import api_views
from .webhook import RazorpayWebhookView

urlpatterns = [
    path('',         api_views.list_payments,    name='api_list_payments'),
    path('summary/', api_views.payment_summary,  name='api_payment_summary'),
    path('webhook/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
]
