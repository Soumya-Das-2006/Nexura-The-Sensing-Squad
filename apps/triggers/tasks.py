"""
apps/triggers/tasks.py

Celery periodic tasks — the trigger engine heart.

Schedule (defined in settings.CELERY_BEAT_SCHEDULE):
  poll_weather_all_zones   → every 15 minutes
  poll_aqi_all_zones       → every 30 minutes
  poll_platform_uptime     → every 10 minutes

Each task:
  1. Fetches live data from the external API (or mocked response in dev)
  2. Runs threshold evaluation (thresholds.py)
  3. Creates a DisruptionEvent if a threshold is breached
  4. Queues the claim-generation task (apps.claims.tasks.process_pending_claims)
     by setting claims_generated=False on the new event
"""
import logging
import requests
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.zones.models import Zone
from .models import DisruptionEvent
from .thresholds import evaluate_rain, evaluate_heat, evaluate_aqi, evaluate_platform_downtime

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

@shared_task(name='apps.triggers.tasks.poll_weather_all_zones', bind=True, max_retries=3)
def poll_weather_all_zones(self):
    """
    Poll OpenWeatherMap for all active zones every 15 minutes.
    Evaluates heavy_rain and extreme_heat triggers.
    """
    api_key = settings.OPENWEATHER_API_KEY
    zones   = Zone.objects.filter(active=True)

    triggered = 0

    for zone in zones:
        try:
            if not api_key:
                # ── MOCK for dev/test ─────────────────────────────────────
                data = _mock_weather(zone)
            else:
                url = (
                    f"https://api.openweathermap.org/data/2.5/weather"
                    f"?lat={zone.lat}&lon={zone.lng}"
                    f"&appid={api_key}&units=metric"
                )
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()

            rain_mm   = data.get('rain', {}).get('1h', 0.0)
            temp_c    = data.get('main', {}).get('temp', 25.0)

            # ── Rain check ────────────────────────────────────────────────
            is_trig, is_full, sev = evaluate_rain(rain_mm)
            if is_trig and not _event_already_open(zone, 'heavy_rain'):
                _create_event(
                    zone, 'heavy_rain', sev,
                    threshold=35.0, is_full=is_full,
                    source_api='openweathermap', raw_payload=data,
                )
                triggered += 1

            # ── Heat check ────────────────────────────────────────────────
            is_trig, is_full, sev = evaluate_heat(temp_c)
            if is_trig and not _event_already_open(zone, 'extreme_heat'):
                _create_event(
                    zone, 'extreme_heat', sev,
                    threshold=42.0, is_full=is_full,
                    source_api='openweathermap', raw_payload=data,
                )
                triggered += 1

        except requests.RequestException as exc:
            logger.warning("[poll_weather] Zone %s — API error: %s", zone, exc)
        except Exception as exc:
            logger.error("[poll_weather] Zone %s — unexpected error: %s", zone, exc, exc_info=True)

    logger.info("[poll_weather] Checked %d zones — %d triggers created.", zones.count(), triggered)
    return {'zones_checked': zones.count(), 'triggers_created': triggered}


# ─── Task 2: AQI polling ──────────────────────────────────────────────────────

@shared_task(name='apps.triggers.tasks.poll_aqi_all_zones', bind=True, max_retries=3)
def poll_aqi_all_zones(self):
    """
    Poll WAQI for all active zones every 30 minutes.
    Evaluates severe_aqi trigger.
    """
    api_key = settings.WAQI_API_KEY
    zones   = Zone.objects.filter(active=True)
    triggered = 0

    for zone in zones:
        try:
            if not api_key:
                data = _mock_aqi(zone)
                aqi  = data.get('aqi', 0)
            else:
                url = (
                    f"https://api.waqi.info/feed/geo:{zone.lat};{zone.lng}/"
                    f"?token={api_key}"
                )
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                aqi  = data.get('data', {}).get('aqi', 0)

            is_trig, is_full, sev = evaluate_aqi(float(aqi))
            if is_trig and not _event_already_open(zone, 'severe_aqi', within_minutes=90):
                _create_event(
                    zone, 'severe_aqi', sev,
                    threshold=300.0, is_full=is_full,
                    source_api='waqi', raw_payload=data,
                )
                triggered += 1

        except requests.RequestException as exc:
            logger.warning("[poll_aqi] Zone %s — API error: %s", zone, exc)
        except Exception as exc:
            logger.error("[poll_aqi] Zone %s — unexpected error: %s", zone, exc, exc_info=True)

    logger.info("[poll_aqi] Checked %d zones — %d triggers created.", zones.count(), triggered)
    return {'zones_checked': zones.count(), 'triggers_created': triggered}


# ─── Task 3: Platform uptime polling ─────────────────────────────────────────

# Track when each platform first went down
# Uses Redis for persistence across worker restarts; falls back to in-memory dict
_platform_down_fallback: dict[str, datetime] = {}

PLATFORM_DOWN_KEY = "nexura:platform_down_since:{platform}"


def _get_redis():
    """Get a Redis connection for platform tracking."""
    import redis as redis_client
    return redis_client.from_url(
        getattr(settings, 'REDIS_URL', '') or 'redis://localhost:6379/0',
        decode_responses=True,
    )


def _get_platform_down_since(platform: str):
    """Return the datetime when platform went down, or None."""
    try:
        r = _get_redis()
        val = r.get(PLATFORM_DOWN_KEY.format(platform=platform))
        return datetime.fromisoformat(val) if val else None
    except Exception:
        return _platform_down_fallback.get(platform)


def _set_platform_down_since(platform: str, dt):
    """Record that platform went down at dt. Expires in 12 hours."""
    try:
        r = _get_redis()
        r.setex(
            PLATFORM_DOWN_KEY.format(platform=platform),
            43200,  # 12 hours TTL
            dt.isoformat(),
        )
    except Exception:
        _platform_down_fallback[platform] = dt


def _clear_platform_down(platform: str):
    """Mark platform as recovered."""
    try:
        r = _get_redis()
        r.delete(PLATFORM_DOWN_KEY.format(platform=platform))
    except Exception:
        _platform_down_fallback.pop(platform, None)


PLATFORM_STATUS_URLS = {
    'zomato':  'https://www.zomato.com/robots.txt',
    'swiggy':  'https://www.swiggy.com/robots.txt',
    'amazon':  'https://www.amazon.in/robots.txt',
    'zepto':   'https://www.zepto.io/robots.txt',
    'blinkit': 'https://blinkit.com/robots.txt',
    'dunzo':   'https://www.dunzo.com/robots.txt',
}


@shared_task(name='apps.triggers.tasks.poll_platform_uptime', bind=True, max_retries=2)
def poll_platform_uptime(self):
    """
    Ping each delivery platform's URL every 10 minutes.
    Creates a platform_down DisruptionEvent for ALL active zones
    when a platform has been unreachable for > 30 minutes.
    """
    triggered = 0
    zones     = Zone.objects.filter(active=True)
    now       = timezone.now()

    for platform, url in PLATFORM_STATUS_URLS.items():
        is_down = False
        try:
            resp = requests.get(url, timeout=8, allow_redirects=True)
            if resp.status_code >= 500:
                is_down = True
        except requests.RequestException:
            is_down = True

        if is_down:
            if _get_platform_down_since(platform) is None:
                _set_platform_down_since(platform, now)
                logger.info("[platform_uptime] %s went down at %s", platform, now)

            down_since   = _get_platform_down_since(platform)
            minutes_down = (now - down_since).total_seconds() / 60

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
            # Platform recovered — close open events
            if _get_platform_down_since(platform) is not None:
                logger.info("[platform_uptime] %s recovered.", platform)
                _clear_platform_down(platform)

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
    from apps.claims.tasks import process_pending_claims
    process_pending_claims.delay()

    return {'event_id': event.pk, 'zone': str(zone), 'trigger_type': trigger_type}


# ─── Mock data helpers (dev / OTP_TEST_MODE) ─────────────────────────────────

def _mock_weather(zone) -> dict:
    """Return realistic mock weather data for a zone based on city."""
    city_mocks = {
        'Mumbai':    {'rain': {'1h': 38.5}, 'main': {'temp': 29.0}},  # triggers rain
        'Delhi':     {'rain': {'1h': 2.0},  'main': {'temp': 44.5}},  # triggers heat
        'Bangalore': {'rain': {'1h': 5.0},  'main': {'temp': 27.0}},
        'Chennai':   {'rain': {'1h': 12.0}, 'main': {'temp': 36.0}},
        'Hyderabad': {'rain': {'1h': 8.0},  'main': {'temp': 39.5}},
        'Kolkata':   {'rain': {'1h': 22.0}, 'main': {'temp': 32.0}},  # partial rain
        'Pune':      {'rain': {'1h': 3.0},  'main': {'temp': 31.0}},
    }
    return city_mocks.get(zone.city, {'rain': {'1h': 0.0}, 'main': {'temp': 28.0}})


def _mock_aqi(zone) -> dict:
    """Return realistic mock AQI data for a zone based on city."""
    city_mocks = {
        'Delhi':     {'aqi': 325},   # triggers full AQI
        'Mumbai':    {'aqi': 155},
        'Kolkata':   {'aqi': 215},   # partial AQI
        'Bangalore': {'aqi': 85},
        'Chennai':   {'aqi': 110},
        'Hyderabad': {'aqi': 130},
        'Pune':      {'aqi': 95},
    }
    aqi = city_mocks.get(zone.city, {'aqi': 80})['aqi']
    return {'data': {'aqi': aqi, 'city': {'name': zone.city}}}
