# apps/zones/api_urls.py
from django.urls import path
from . import api_views

urlpatterns = [
    path('',             api_views.ZoneListAPIView.as_view(),     name='zone_list'),
    path('<int:pk>/',    api_views.ZoneDetailAPIView.as_view(),   name='zone_detail'),
    path('by-city/',     api_views.ZonesByCityAPIView.as_view(),  name='zones_by_city'),
]
