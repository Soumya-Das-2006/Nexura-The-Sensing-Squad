# apps/payouts/urls.py
from django.urls import path
from . import views

app_name = 'payouts'

urlpatterns = [
    path('payouts/', views.history, name='history'),
]
