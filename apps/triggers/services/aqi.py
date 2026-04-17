"""
apps/triggers/services/aqi.py

Production-grade AQI service for WAQI (World Air Quality Index) API.
Handles HTTP retries, timeouts, response validation, and mock fallback.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ─── Custom Exception ─────────────────────────────────────────────────────────

class AQIAPIError(Exception):
    """Raised when the WAQI API call fails after all retries."""

    def __init__(self, message: str, zone=None, status_code: int = None):
        self.zone = zone
        self.status_code = status_code
        super().__init__(message)


# ─── Data Transfer Object ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class AQIData:
    """Clean, validated AQI data returned by the service."""
    aqi_value: float = 0.0
    station_name: str = ""
    dominant_pollutant: str = ""
    raw_payload: dict = field(default_factory=dict)

    @property
    def category(self) -> str:
        if self.aqi_value <= 50: return "Good"
        if self.aqi_value <= 100: return "Moderate"
        if self.aqi_value <= 150: return "Unhealthy for Sensitive Groups"
        if self.aqi_value <= 200: return "Unhealthy"
        if self.aqi_value <= 300: return "Very Unhealthy"
        return "Hazardous"

    @property
    def color(self) -> str:
        if self.aqi_value <= 50: return "#009966"
        if self.aqi_value <= 100: return "#FFDE33"
        if self.aqi_value <= 150: return "#FF9933"
        if self.aqi_value <= 200: return "#CC0033"
        if self.aqi_value <= 300: return "#660099"
        return "#7E0023"


# ─── Service ──────────────────────────────────────────────────────────────────

class AQIService:
    """
    Encapsulates all WAQI API interaction.

    Usage:
        service = AQIService()
        data = service.fetch_aqi(zone)   # returns AQIData
    """

    BASE_URL = "https://api.waqi.info/feed/geo:{lat};{lng}/"
    TIMEOUT = 10  # seconds

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, 'WAQI_API_KEY', '')
        self._session = self._build_session()

    # ── Public API ────────────────────────────────────────────────────────

    def fetch_aqi(self, zone) -> AQIData:
        """
        Fetch current AQI for a zone.
        Falls back to mock data when no API key is configured.
        Uses city-level caching to prevent redundant API calls for zones in the same city.

        Args:
            zone: Zone model instance (must have .lat, .lng, .city)

        Returns:
            AQIData dataclass

        Raises:
            AQIAPIError: on HTTP or parsing failures
        """
        if not self._api_key:
            logger.debug(
                "[AQIService] No API key — returning mock data for zone=%s",
                zone,
            )
            return self._mock_aqi(zone)

        # ── City-level deduplication cache ──
        cache_key = f"waqi_city_{zone.city.replace(' ', '_').lower()}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.debug("[AQIService] Cache hit for city=%s (zone=%s)", zone.city, zone)
            
            # Create a copy with 'cached': True in the payload
            raw = dict(cached_data.raw_payload)
            raw['cached'] = True
            return AQIData(
                aqi_value=cached_data.aqi_value,
                station_name=cached_data.station_name,
                dominant_pollutant=cached_data.dominant_pollutant,
                raw_payload=raw,
            )

        # ── Fetch fresh and cache for 20 mins ──
        data = self._fetch_live(zone)
        cache.set(cache_key, data, timeout=20 * 60)
        return data

    # ── Private: live API call ────────────────────────────────────────────

    def _fetch_live(self, zone) -> AQIData:
        """Make the actual HTTP call to WAQI."""
        url = self.BASE_URL.format(lat=zone.lat, lng=zone.lng)
        params = {'token': self._api_key}

        try:
            logger.info(
                "[AQIService] Polling zone=%s (lat=%.4f, lon=%.4f)",
                zone, zone.lat, zone.lng,
            )
            response = self._session.get(
                url,
                params=params,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else None
            logger.error(
                "[AQIService] HTTP %s for zone=%s: %s",
                status, zone, exc,
            )
            raise AQIAPIError(
                f"WAQI HTTP {status} for zone {zone}",
                zone=zone,
                status_code=status,
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error(
                "[AQIService] Connection error for zone=%s: %s",
                zone, exc,
            )
            raise AQIAPIError(
                f"Connection error fetching AQI for zone {zone}",
                zone=zone,
            ) from exc

        except requests.exceptions.Timeout as exc:
            logger.error(
                "[AQIService] Timeout for zone=%s after %ds",
                zone, self.TIMEOUT,
            )
            raise AQIAPIError(
                f"Timeout fetching AQI for zone {zone}",
                zone=zone,
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.error(
                "[AQIService] Request failed for zone=%s: %s",
                zone, exc,
            )
            raise AQIAPIError(
                f"Request failed for zone {zone}: {exc}",
                zone=zone,
            ) from exc

        # WAQI returns {"status": "ok", "data": {...}} — validate status
        if data.get('status') != 'ok':
            error_msg = data.get('data', 'Unknown WAQI error')
            logger.error(
                "[AQIService] WAQI returned non-ok status for zone=%s: %s",
                zone, error_msg,
            )
            raise AQIAPIError(
                f"WAQI error for zone {zone}: {error_msg}",
                zone=zone,
            )

        return self._parse_response(data, zone)

    # ── Private: parse + validate ─────────────────────────────────────────

    def _parse_response(self, data: dict, zone) -> AQIData:
        """Parse WAQI JSON into an AQIData object."""
        try:
            inner = data.get('data', {})
            city_info = inner.get('city', {})

            return AQIData(
                aqi_value=float(inner.get('aqi', 0)),
                station_name=city_info.get('name', ''),
                dominant_pollutant=inner.get('dominentpol', ''),
                raw_payload=data,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error(
                "[AQIService] Failed to parse response for zone=%s: %s | raw=%s",
                zone, exc, data,
            )
            raise AQIAPIError(
                f"Failed to parse AQI response for zone {zone}",
                zone=zone,
            ) from exc

    # ── Private: HTTP session with retry ──────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        """Build a requests Session with automatic retry on transient errors."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,                   # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ── Private: mock data ────────────────────────────────────────────────

    @staticmethod
    def _mock_aqi(zone) -> AQIData:
        """Return realistic mock AQI data for a zone based on city."""
        city_mocks = {
            'Delhi':     325,   # triggers full AQI
            'Mumbai':    155,
            'Kolkata':   215,   # partial AQI
            'Bangalore': 85,
            'Chennai':   110,
            'Hyderabad': 130,
            'Pune':      95,
        }
        aqi = city_mocks.get(zone.city, 80)
        return AQIData(
            aqi_value=float(aqi),
            station_name=f"{zone.city} (mock)",
            raw_payload={'mock': True, 'city': zone.city, 'aqi': aqi},
        )
