"""
apps/triggers/services/uptime.py

Production-grade Uptime Service for pinging delivery platforms.
"""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class UptimeService:
    """
    Encapsulates network logic for pinging platform endpoints.
    Handles timeouts and retries for transient errors.
    """
    TIMEOUT = 8  # seconds

    def __init__(self):
        self._session = self._build_session()

    def check_is_down(self, platform_name: str, url: str) -> bool:
        """
        Pings a URL and returns True if it's considered down.
        A 500+ status code or connection failure means it's down.
        """
        try:
            response = self._session.get(url, timeout=self.TIMEOUT, allow_redirects=True)
            if response.status_code >= 500:
                logger.warning("[UptimeService] %s returned status %s", platform_name, response.status_code)
                return True
            return False
        except requests.RequestException as exc:
            logger.warning("[UptimeService] %s check failed: %s", platform_name, exc)
            return True

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        # 3 retries, total backoff: 0.5, 1.0, 2.0 seconds
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
