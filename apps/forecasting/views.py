"""
apps/forecasting/views.py

/forecast/  → Worker's zone risk forecast for the coming week.
              Also shows all-city overview for context.
"""
import logging
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

logger = logging.getLogger(__name__)
_login = login_required(login_url='accounts:login')


@_login
def zone_forecast(request):
    """Worker's personalised forecast page."""
    if not request.user.is_worker:
        return redirect('core:home')

    from apps.zones.models import Zone
    from .models import ZoneForecast
    from .loader import load_all_models, models_available, forecast_city_week, _next_monday

    if not models_available():
        load_all_models()

    today      = timezone.now().date()
    week_start = _next_monday(today)

    # Worker's zone forecast
    worker_forecast = None
    worker_zone     = None
    try:
        profile     = request.user.workerprofile
        worker_zone = profile.zone
        if worker_zone:
            worker_forecast = ZoneForecast.objects.filter(
                zone=worker_zone, forecast_date=week_start
            ).first()
            # If not generated yet, run on-demand
            if not worker_forecast:
                result = forecast_city_week(worker_zone.city, week_start)
                worker_forecast, _ = ZoneForecast.objects.update_or_create(
                    zone=worker_zone, forecast_date=week_start,
                    defaults={
                        'rain_probability':       result.rain_probability,
                        'heat_probability':       result.heat_probability,
                        'aqi_probability':        result.aqi_probability,
                        'disruption_probability': result.disruption_probability,
                        'forecasted_rain_mm':     result.forecasted_rain_mm,
                        'forecasted_temp_c':      result.forecasted_temp_c,
                        'forecasted_aqi':         result.forecasted_aqi,
                        'overall_risk_level':     result.overall_risk_level,
                    },
                )
    except Exception as exc:
        logger.warning("[forecast_view] Could not load worker forecast: %s", exc)

    # All cities overview — latest forecast per city
    all_city_forecasts = []
    # Reset model default ordering before distinct() to avoid duplicates per area_name.
    cities = Zone.objects.filter(active=True).order_by().values_list('city', flat=True).distinct().order_by('city')
    for city in cities:
        zone = Zone.objects.filter(city=city, active=True).first()
        if not zone:
            continue
        fc = ZoneForecast.objects.filter(zone=zone, forecast_date=week_start).first()
        if not fc:
            try:
                result = forecast_city_week(zone.city, week_start)
                fc, _ = ZoneForecast.objects.update_or_create(
                    zone=zone, forecast_date=week_start,
                    defaults={
                        'rain_probability':       result.rain_probability,
                        'heat_probability':       result.heat_probability,
                        'aqi_probability':        result.aqi_probability,
                        'disruption_probability': result.disruption_probability,
                        'forecasted_rain_mm':     result.forecasted_rain_mm,
                        'forecasted_temp_c':      result.forecasted_temp_c,
                        'forecasted_aqi':         result.forecasted_aqi,
                        'overall_risk_level':     result.overall_risk_level,
                    },
                )
            except Exception as exc:
                logger.warning('[forecast_view] Could not generate forecast for %s: %s', city, exc)
                continue
        all_city_forecasts.append(fc)

    # Historical forecasts for worker's zone (last 4 weeks)
    history = []
    if worker_zone:
        history = ZoneForecast.objects.filter(
            zone=worker_zone,
            forecast_date__lt=week_start,
        ).order_by('-forecast_date')[:4]

    ctx = {
        'worker_forecast':     worker_forecast,
        'worker_zone':         worker_zone,
        'all_city_forecasts':  all_city_forecasts,
        'history':             history,
        'week_start':          week_start,
        'week_end':            week_start + timedelta(days=6),
    }
    return render(request, 'forecasting/zone_forecast.html', ctx)
