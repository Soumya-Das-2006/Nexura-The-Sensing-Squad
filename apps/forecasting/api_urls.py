# apps/forecasting/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('my-zone/',        api_views.my_zone_forecast, name='api_my_zone_forecast'),
    path('city/<str:city>/', api_views.city_forecast,  name='api_city_forecast'),
    path('all/',            api_views.all_forecasts,    name='api_all_forecasts'),
    path('generate/',       api_views.trigger_generation, name='api_generate_forecasts'),
]
