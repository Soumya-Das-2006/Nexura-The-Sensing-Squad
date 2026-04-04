"""
apps/forecasting/tasks.py

generate_zone_forecasts
    Runs every Sunday at 8:30 PM IST.
    For every active city, runs all 4 Prophet models (rain/heat/AQI/disruption),
    aggregates per-zone, and writes/updates ZoneForecast records.

send_forecast_alerts
    Runs every Sunday at 9:00 PM IST (30 min after generation).
    Sends WhatsApp + email forecasts to all active workers.
"""
import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _next_monday(ref: date = None) -> date:
    today = ref or timezone.now().date()
    days  = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


# ─── Task 1: Generate forecasts ───────────────────────────────────────────────

@shared_task(name='apps.forecasting.tasks.generate_zone_forecasts')
def generate_zone_forecasts():
    """
    Sunday 8:30 PM — run Prophet models for all 7 cities and persist ZoneForecasts.
    """
    from apps.zones.models import Zone
    from .models import ZoneForecast
    from .loader import load_all_models, models_available, forecast_city_week

    if not models_available():
        load_all_models()

    week_start = _next_monday()
    logger.info("[forecasting] Generating forecasts for week starting %s", week_start)

    # Run one forecast per city (not per zone) — zones in the same city share the forecast
    city_forecasts = {}
    cities = Zone.objects.filter(active=True).values_list('city', flat=True).distinct()

    for city in cities:
        result = forecast_city_week(city, week_start)
        city_forecasts[city] = result
        logger.info(
            "[forecasting] %s → risk=%s rain=%.2f heat=%.2f aqi=%.2f disruption=%.2f (model=%s)",
            city, result.overall_risk_level,
            result.rain_probability, result.heat_probability,
            result.aqi_probability, result.disruption_probability,
            result.model_used,
        )

    # Persist one ZoneForecast record per zone
    zones   = Zone.objects.filter(active=True)
    created = 0
    updated = 0

    for zone in zones:
        result = city_forecasts.get(zone.city)
        if result is None:
            continue

        obj, is_new = ZoneForecast.objects.update_or_create(
            zone          = zone,
            forecast_date = week_start,
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
        if is_new:
            created += 1
        else:
            updated += 1

    logger.info(
        "[forecasting] Done — %d created, %d updated for %d zones.",
        created, updated, zones.count(),
    )
    return {
        'week_start': str(week_start),
        'cities':     len(city_forecasts),
        'zones':      zones.count(),
        'created':    created,
        'updated':    updated,
    }


# ─── Task 2: Send forecast alerts ────────────────────────────────────────────

@shared_task(name='apps.forecasting.tasks.send_forecast_alerts')
def send_forecast_alerts():
    """
    Sunday 9:00 PM — send weekly risk forecasts via WhatsApp + email.
    Only sends to workers whose zone has Moderate or above risk.
    """
    from apps.policies.models import Policy
    from .models import ZoneForecast

    week_start = _next_monday()
    sent = 0
    skipped = 0

    active_policies = Policy.objects.filter(
        status='active',
    ).select_related(
        'worker', 'worker__workerprofile', 'worker__workerprofile__zone',
    )

    for policy in active_policies:
        worker  = policy.worker
        profile = getattr(worker, 'workerprofile', None)
        zone    = getattr(profile, 'zone', None)

        if not zone:
            skipped += 1
            continue

        try:
            forecast = ZoneForecast.objects.get(zone=zone, forecast_date=week_start)
        except ZoneForecast.DoesNotExist:
            skipped += 1
            continue

        # Only alert on non-trivial risk
        if forecast.overall_risk_level == 'Low':
            skipped += 1
            continue

        try:
            from apps.notifications.tasks import send_forecast_notification
            send_forecast_notification.delay(worker.pk, forecast.pk)
            sent += 1
        except Exception as exc:
            logger.warning("[forecasting] Alert failed for %s: %s", worker.mobile, exc)

    logger.info("[forecasting] Alerts — %d sent, %d skipped.", sent, skipped)
    return {'sent': sent, 'skipped': skipped}
