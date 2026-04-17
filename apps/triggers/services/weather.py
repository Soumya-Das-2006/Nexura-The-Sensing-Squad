"""
apps/triggers/services/weather.py

Production-grade weather service for OpenWeatherMap API.
Handles HTTP retries, timeouts, response validation, and mock fallback.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── Custom Exception ─────────────────────────────────────────────────────────

class WeatherAPIError(Exception):
    """Raised when the OpenWeatherMap API call fails after all retries."""

    def __init__(self, message: str, zone=None, status_code: int = None):
        self.zone = zone
        self.status_code = status_code
        super().__init__(message)


# ─── Data Transfer Object ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class WeatherData:
    """Clean, validated weather data returned by the service."""
    rain_mm: float = 0.0
    temp_c: float = 25.0
    humidity: float = 0.0
    wind_speed: float = 0.0
    description: str = ""
    raw_payload: dict = field(default_factory=dict)


# ─── Service ──────────────────────────────────────────────────────────────────

class WeatherService:
    """
    Encapsulates all OpenWeatherMap API interaction.

    Usage:
        service = WeatherService()
        data = service.fetch_weather(zone)   # returns WeatherData
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    TIMEOUT = 10  # seconds

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or getattr(settings, 'OPENWEATHER_API_KEY', '')
        self._session = self._build_session()

    # ── Public API ────────────────────────────────────────────────────────

    def fetch_weather(self, zone) -> WeatherData:
        """
        Fetch current weather for a zone.
        Falls back to mock data when no API key is configured.

        Args:
            zone: Zone model instance (must have .lat, .lng, .city)

        Returns:
            WeatherData dataclass

        Raises:
            WeatherAPIError: on HTTP or parsing failures
        """
        if not self._api_key:
            logger.debug(
                "[WeatherService] No API key — returning mock data for zone=%s",
                zone,
            )
            return self._mock_weather(zone)

        return self._fetch_live(zone)

    # ── Private: live API call ────────────────────────────────────────────

    def _fetch_live(self, zone) -> WeatherData:
        """Make the actual HTTP call to OpenWeatherMap."""
        params = {
            'lat': zone.lat,
            'lon': zone.lng,
            'appid': self._api_key,
            'units': 'metric',
        }

        try:
            logger.info(
                "[WeatherService] Polling zone=%s (lat=%.4f, lon=%.4f)",
                zone, zone.lat, zone.lng,
            )
            response = self._session.get(
                self.BASE_URL,
                params=params,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response else None
            logger.error(
                "[WeatherService] HTTP %s for zone=%s: %s",
                status, zone, exc,
            )
            raise WeatherAPIError(
                f"OpenWeatherMap HTTP {status} for zone {zone}",
                zone=zone,
                status_code=status,
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error(
                "[WeatherService] Connection error for zone=%s: %s",
                zone, exc,
            )
            raise WeatherAPIError(
                f"Connection error fetching weather for zone {zone}",
                zone=zone,
            ) from exc

        except requests.exceptions.Timeout as exc:
            logger.error(
                "[WeatherService] Timeout for zone=%s after %ds",
                zone, self.TIMEOUT,
            )
            raise WeatherAPIError(
                f"Timeout fetching weather for zone {zone}",
                zone=zone,
            ) from exc

        except requests.exceptions.RequestException as exc:
            logger.error(
                "[WeatherService] Request failed for zone=%s: %s",
                zone, exc,
            )
            raise WeatherAPIError(
                f"Request failed for zone {zone}: {exc}",
                zone=zone,
            ) from exc

        return self._parse_response(data, zone)

    # ── Private: parse + validate ─────────────────────────────────────────

    def _parse_response(self, data: dict, zone) -> WeatherData:
        """Parse OpenWeatherMap JSON into a WeatherData object."""
        try:
            main = data.get('main', {})
            wind = data.get('wind', {})
            rain = data.get('rain', {})
            weather_list = data.get('weather', [{}])

            return WeatherData(
                rain_mm=float(rain.get('1h', 0.0)),
                temp_c=float(main.get('temp', 25.0)),
                humidity=float(main.get('humidity', 0.0)),
                wind_speed=float(wind.get('speed', 0.0)),
                description=weather_list[0].get('description', '') if weather_list else '',
                raw_payload=data,
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            logger.error(
                "[WeatherService] Failed to parse response for zone=%s: %s | raw=%s",
                zone, exc, data,
            )
            raise WeatherAPIError(
                f"Failed to parse weather response for zone {zone}",
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
    def _mock_weather(zone) -> WeatherData:
        """Return realistic mock weather data for a zone based on city."""
        city_mocks = {
            'Mumbai':    {'rain_mm': 38.5, 'temp_c': 29.0},
            'Delhi':     {'rain_mm': 2.0,  'temp_c': 44.5},
            'Bangalore': {'rain_mm': 5.0,  'temp_c': 27.0},
            'Chennai':   {'rain_mm': 12.0, 'temp_c': 36.0},
            'Hyderabad': {'rain_mm': 8.0,  'temp_c': 39.5},
            'Kolkata':   {'rain_mm': 22.0, 'temp_c': 32.0},
            'Pune':      {'rain_mm': 3.0,  'temp_c': 31.0},
        }
        mock = city_mocks.get(zone.city, {'rain_mm': 0.0, 'temp_c': 28.0})
        return WeatherData(
            rain_mm=mock['rain_mm'],
            temp_c=mock['temp_c'],
            raw_payload={'mock': True, 'city': zone.city},
        )
