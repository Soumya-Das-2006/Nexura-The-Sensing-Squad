"""
apps/triggers/tasks.py

Celery periodic tasks — the trigger engine heart.

Schedule (defined in settings.CELERY_BEAT_SCHEDULE):
  poll_weather_all_zones   → every 15 minutes
  poll_aqi_all_zones       → every 30 minutes
  poll_platform_uptime     → every 10 minutes

Each task:
  1. Delegates API calls to the services layer (services/)
  2. Runs threshold evaluation (thresholds.py)
  3. Creates a DisruptionEvent if a threshold is breached
  4. Queues the claim-generation task (apps.claims.tasks.process_pending_claims)
     by setting claims_generated=False on the new event
"""
import logging
from datetime import datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.zones.models import Zone
from .models import DisruptionEvent
from .thresholds import evaluate_rain, evaluate_heat, evaluate_aqi, evaluate_platform_downtime
from .services.weather import WeatherService, WeatherAPIError
from .services.aqi import AQIService, AQIAPIError

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _event_already_open(zone, trigger_type: str, within_minutes: int = 60) -> bool:
    """
    Guard against duplicate events.
    Returns True if a DisruptionEvent of the same type already exists
    for this zone within the last `within_minutes`.
    """
    cutoff = timezone.now() - timedelta(minutes=within_minutes)
    return DisruptionEvent.objects.filter(
        zone=zone,
        trigger_type=trigger_type,
        started_at__gte=cutoff,
        ended_at__isnull=True,
    ).exists()


def _create_event(zone, trigger_type, severity, threshold, is_full,
                  source_api='', affected_platform='all', raw_payload=None):
    """Create a DisruptionEvent and log it."""
    event = DisruptionEvent.objects.create(
        zone=zone,
        trigger_type=trigger_type,
        severity_value=severity,
        threshold_value=threshold,
        is_full_trigger=is_full,
        affected_platform=affected_platform,
        source_api=source_api,
        raw_payload=raw_payload or {},
    )
    logger.info(
        "[TRIGGER] %s in %s | severity=%.2f | full=%s | event_id=%s",
        trigger_type, zone, severity, is_full, event.pk,
    )
    return event


# ─── Task 1: Weather polling (rain + heat) ────────────────────────────────────

@shared_task(
    name='apps.triggers.tasks.poll_weather_all_zones',
    bind=True,
    max_retries=3,
    autoretry_for=(WeatherAPIError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def poll_weather_all_zones(self):
    """
    Poll OpenWeatherMap for all active zones every 15 minutes.
    Evaluates heavy_rain and extreme_heat triggers.

    Auto-retries on WeatherAPIError with exponential backoff.
    """
    weather_service = WeatherService()
    zones = Zone.objects.filter(active=True)
    triggered = 0
    errors = 0

    for zone in zones:
        try:
            weather_data = weather_service.fetch_weather(zone)

            rain_mm = weather_data.rain_mm
            temp_c = weather_data.temp_c
            raw = weather_data.raw_payload

            # ── Rain check ────────────────────────────────────────────────
            is_trig, is_full, sev = evaluate_rain(rain_mm)
            if is_trig and not _event_already_open(zone, 'heavy_rain'):
                _create_event(
                    zone, 'heavy_rain', sev,
                    threshold=35.0, is_full=is_full,
                    source_api='openweathermap', raw_payload=raw,
                )
                triggered += 1

            # ── Heat check ────────────────────────────────────────────────
            is_trig, is_full, sev = evaluate_heat(temp_c)
            if is_trig and not _event_already_open(zone, 'extreme_heat'):
                _create_event(
                    zone, 'extreme_heat', sev,
                    threshold=42.0, is_full=is_full,
                    source_api='openweathermap', raw_payload=raw,
                )
                triggered += 1

            logger.debug(
                "[poll_weather] zone=%s rain=%.1fmm temp=%.1f°C",
                zone, rain_mm, temp_c,
            )

        except WeatherAPIError as exc:
            errors += 1
            logger.warning(
                "[poll_weather] Zone %s — weather API error (zone skipped): %s",
                zone, exc,
            )
            # Continue to next zone — don't let one zone failure abort the batch

        except Exception as exc:
            errors += 1
            logger.error(
                "[poll_weather] Zone %s — unexpected error: %s",
                zone, exc, exc_info=True,
            )

    logger.info(
        "[poll_weather] Completed: zones_checked=%d triggers_created=%d errors=%d",
        zones.count(), triggered, errors,
    )
    return {
        'zones_checked': zones.count(),
        'triggers_created': triggered,
        'errors': errors,
    }


# ─── Task 2: AQI polling ──────────────────────────────────────────────────────

@shared_task(
    name='apps.triggers.tasks.poll_aqi_all_zones',
    bind=True,
    max_retries=3,
    autoretry_for=(AQIAPIError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def poll_aqi_all_zones(self):
    """
    Poll WAQI for all active zones every 30 minutes.
    Evaluates severe_aqi trigger.

    Auto-retries on AQIAPIError with exponential backoff.
    """
    aqi_service = AQIService()
    zones = Zone.objects.filter(active=True)
    triggered = 0
    errors = 0

    for zone in zones:
        try:
            aqi_data = aqi_service.fetch_aqi(zone)
            aqi_value = aqi_data.aqi_value
            raw = aqi_data.raw_payload

            is_trig, is_full, sev = evaluate_aqi(aqi_value)
            if is_trig and not _event_already_open(zone, 'severe_aqi', within_minutes=90):
                _create_event(
                    zone, 'severe_aqi', sev,
                    threshold=300.0, is_full=is_full,
                    source_api='waqi', raw_payload=raw,
                )
                triggered += 1

            logger.debug(
                "[poll_aqi] zone=%s aqi=%.0f",
                zone, aqi_value,
            )

        except AQIAPIError as exc:
            errors += 1
            logger.warning(
                "[poll_aqi] Zone %s — AQI API error (zone skipped): %s",
                zone, exc,
            )

        except Exception as exc:
            errors += 1
            logger.error(
                "[poll_aqi] Zone %s — unexpected error: %s",
                zone, exc, exc_info=True,
            )

    logger.info(
        "[poll_aqi] Completed: zones_checked=%d triggers_created=%d errors=%d",
        zones.count(), triggered, errors,
    )
    return {
        'zones_checked': zones.count(),
        'triggers_created': triggered,
        'errors': errors,
    }


# ─── Task 3: Platform uptime polling ─────────────────────────────────────────

from .models import PlatformDowntimeState
from .services.uptime import UptimeService

PLATFORM_STATUS_URLS = {
    'zomato':  'https://www.zomato.com/robots.txt',
    'swiggy':  'https://www.swiggy.com/robots.txt',
    'amazon':  'https://www.amazon.in/robots.txt',
    'zepto':   'https://www.zepto.io/robots.txt',
    'blinkit': 'https://blinkit.com/robots.txt',
    'dunzo':   'https://www.dunzo.com/robots.txt',
}


@shared_task(
    name='apps.triggers.tasks.poll_platform_uptime',
    bind=True,
    max_retries=2,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def poll_platform_uptime(self):
    """
    Ping each delivery platform's URL every 10 minutes.
    Creates a platform_down DisruptionEvent for ALL active zones
    when a platform has been unreachable for > 30 minutes.
    Uses persistent database storage for multi-worker safety.
    """
    triggered = 0
    zones     = Zone.objects.filter(active=True)
    now       = timezone.now()
    uptime_svc = UptimeService()

    for platform, url in PLATFORM_STATUS_URLS.items():
        is_down = uptime_svc.check_is_down(platform, url)

        if is_down:
            # Get or create persistent downtime record
            state, created = PlatformDowntimeState.objects.get_or_create(
                platform_name=platform,
                is_deleted=False,
                defaults={'down_since': now}
            )

            if created:
                logger.info("[platform_uptime] %s went down at %s", platform, now)

            minutes_down = (now - state.down_since).total_seconds() / 60

            is_trig, is_full, sev = evaluate_platform_downtime(minutes_down)
            if is_trig:
                # Create one event per zone that workers in that zone get claims
                for zone in zones:
                    if not _event_already_open(zone, 'platform_down', within_minutes=45):
                        _create_event(
                            zone, 'platform_down', sev,
                            threshold=30.0, is_full=is_full,
                            source_api='uptime_monitor',
                            affected_platform=platform,
                            raw_payload={'platform': platform, 'minutes_down': minutes_down},
                        )
                        triggered += 1
        else:
            # Platform recovered — close open events and soft-delete states
            active_states = PlatformDowntimeState.objects.filter(
                platform_name=platform, 
                is_deleted=False
            )
            
            if active_states.exists():
                logger.info("[platform_uptime] %s recovered.", platform)
                for state in active_states:
                    state.soft_delete()

                DisruptionEvent.objects.filter(
                    trigger_type='platform_down',
                    affected_platform=platform,
                    ended_at__isnull=True,
                ).update(ended_at=now)

    logger.info("[poll_platform_uptime] %d platform_down events created.", triggered)
    return {'triggers_created': triggered}


# ─── Task 4: Manual event creator (called from admin / management cmd) ────────

@shared_task(name='apps.triggers.tasks.create_manual_event')
def create_manual_event(zone_id: int, trigger_type: str,
                        severity: float, is_full: bool = True,
                        source_api: str = 'manual'):
    """
    Manually inject a DisruptionEvent (admin / testing tool).
    Immediately triggers claim generation for that zone.
    """
    try:
        zone = Zone.objects.get(pk=zone_id)
    except Zone.DoesNotExist:
        logger.error("[create_manual_event] Zone %s not found.", zone_id)
        return

    thresholds_map = {
        'heavy_rain':    35.0,
        'extreme_heat':  42.0,
        'severe_aqi':    300.0,
        'flash_flood':   1.0,
        'curfew_strike': 1.0,
        'platform_down': 30.0,
    }

    event = _create_event(
        zone, trigger_type, severity,
        threshold=thresholds_map.get(trigger_type, 0),
        is_full=is_full, source_api=source_api,
    )

    # Immediately queue claim generation
    try:
        from apps.claims.tasks import process_pending_claims
        process_pending_claims.delay()
    except Exception as exc:
        logger.error(
            "[create_manual_event] Failed to queue claim generation: %s",
            exc, exc_info=True,
        )

    return {'event_id': event.pk, 'zone': str(zone), 'trigger_type': trigger_type}
