# apps/pricing/urls.py
from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('calculator/', views.PremiumCalculatorView.as_view(), name='calculator'),
]
