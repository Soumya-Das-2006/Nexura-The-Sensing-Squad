# apps/forecasting/urls.py
from django.urls import path
from . import views

app_name = 'forecasting'

urlpatterns = [
    path('forecast/', views.zone_forecast, name='zone_forecast'),
]
