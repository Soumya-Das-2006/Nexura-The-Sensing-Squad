# apps/payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('payments/history/', views.payment_history, name='history'),
]
