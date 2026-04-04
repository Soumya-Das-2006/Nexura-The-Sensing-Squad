"""
apps/zones/api_views.py

REST API for Zone data.
All endpoints are read-only — zones are managed via Django Admin and fixtures.

Endpoints
---------
GET /api/v1/zones/                   → list all active zones (supports ?city=Mumbai)
GET /api/v1/zones/<id>/              → single zone detail
GET /api/v1/zones/by-city/           → zones grouped by city {city: [zones]}
"""
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Prefetch

from .models import Zone
from .serializers import ZoneSerializer, ZoneListSerializer


class ZoneListAPIView(ListAPIView):
    """
    GET /api/v1/zones/
    Returns all active zones.
    Optional filter: ?city=Mumbai
    """
    serializer_class   = ZoneListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Zone.objects.filter(active=True)
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city=city)
        return qs


class ZoneDetailAPIView(RetrieveAPIView):
    """GET /api/v1/zones/<id>/"""
    serializer_class   = ZoneSerializer
    permission_classes = [AllowAny]
    queryset           = Zone.objects.filter(active=True)


class ZonesByCityAPIView(APIView):
    """
    GET /api/v1/zones/by-city/
    Returns zones grouped by city — used to populate dropdowns.

    Response shape:
    {
      "Mumbai":    [{"id": 1, "area_name": "Andheri", "risk_multiplier": "1.40"}, ...],
      "Delhi":     [...],
      ...
    }
    """
    permission_classes = [AllowAny]

    def get(self, request):
        zones = Zone.objects.filter(active=True).values(
            'id', 'city', 'area_name', 'risk_multiplier'
        )
        grouped = {}
        for z in zones:
            grouped.setdefault(z['city'], []).append({
                'id':              z['id'],
                'area_name':       z['area_name'],
                'risk_multiplier': str(z['risk_multiplier']),
            })
        return Response(grouped)
