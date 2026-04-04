# apps/pricing/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('my-risk/',        api_views.my_risk,              name='api_my_risk'),
    path('calculate/',      api_views.calculate_api,        name='api_calculate'),
    path('model-info/',     api_views.model_info,           name='api_pricing_model_info'),
    path('recalculate/',    api_views.trigger_recalculation, name='api_trigger_recalc'),
]
