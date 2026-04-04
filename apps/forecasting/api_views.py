"""
apps/forecasting/api_views.py

GET  /api/v1/forecasting/my-zone/         → current worker's zone forecast
GET  /api/v1/forecasting/city/<city>/     → forecast for a named city
GET  /api/v1/forecasting/all/             → latest forecast for all cities
POST /api/v1/forecasting/generate/        → trigger generation (admin)
"""
import logging
from datetime import timedelta

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .models import ZoneForecast
from .serializers import ZoneForecastSerializer
from .loader import _next_monday

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_zone_forecast(request):
    """Current worker's zone forecast for the coming week."""
    try:
        zone = request.user.workerprofile.zone
    except Exception:
        return Response({'error': 'Profile or zone not set.'}, status=404)

    week_start = _next_monday()
    fc = ZoneForecast.objects.filter(zone=zone, forecast_date=week_start).first()

    if not fc:
        return Response({'error': 'Forecast not generated yet. Check back Sunday evening.'}, status=404)

    return Response(ZoneForecastSerializer(fc).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def city_forecast(request, city):
    """Latest forecast for any city (public)."""
    from apps.zones.models import Zone
    zone = Zone.objects.filter(city=city, active=True).first()
    if not zone:
        return Response({'error': f'City {city!r} not covered.'}, status=404)

    week_start = _next_monday()
    fc = ZoneForecast.objects.filter(zone=zone, forecast_date=week_start).first()
    if not fc:
        return Response({'error': 'Forecast not yet generated.'}, status=404)

    return Response(ZoneForecastSerializer(fc).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def all_forecasts(request):
    """Latest forecast for all active cities."""
    from apps.zones.models import Zone

    week_start = _next_monday()
    cities     = Zone.objects.filter(active=True).values_list('city', flat=True).distinct()

    results = []
    for city in cities:
        zone = Zone.objects.filter(city=city, active=True).first()
        if zone:
            fc = ZoneForecast.objects.filter(zone=zone, forecast_date=week_start).first()
            if fc:
                results.append(ZoneForecastSerializer(fc).data)

    return Response(results)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_generation(request):
    """Admin: manually trigger forecast generation."""
    from .tasks import generate_zone_forecasts
    task = generate_zone_forecasts.delay()
    return Response({'message': 'Forecast generation queued.', 'task_id': str(task.id)})
