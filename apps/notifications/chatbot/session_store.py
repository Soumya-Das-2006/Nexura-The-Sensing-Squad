"""
apps/notifications/chatbot/session_store.py

User language preference and conversation session management.

Storage backend: Redis (primary) → DB (fallback)

Redis keys:
    chatbot:lang:<phone>          → user's detected language code ('en'/'hi'/'gu')
    chatbot:session:<phone>       → last intent name (for context-aware replies)
    chatbot:msg_count:<phone>     → total messages received (analytics)

TTL: 30 days for language preference, 1 hour for session context.
"""

import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Redis key prefixes
_LANG_KEY    = 'chatbot:lang:{phone}'
_SESSION_KEY = 'chatbot:session:{phone}'
_COUNT_KEY   = 'chatbot:msg_count:{phone}'

LANG_TTL    = 60 * 60 * 24 * 30   # 30 days
SESSION_TTL = 60 * 60              # 1 hour


def _get_redis():
    """Return a Redis connection from Django's cache or a raw redis-py client."""
    try:
        import redis
        url = getattr(settings, 'REDIS_URL', None) or \
              getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
        # Use db=1 to avoid collision with Celery broker (db=0)
        return redis.from_url(url, db=1, decode_responses=True)
    except Exception as exc:
        logger.warning("[SessionStore] Redis unavailable: %s", exc)
        return None


class SessionStore:
    """
    Manages per-user language preference and conversation context.

    All methods are safe to call even when Redis is down (they fall back to
    returning sensible defaults rather than raising).
    """

    def __init__(self, phone: str):
        # Normalize phone: strip whitespace and 'whatsapp:' prefix
        self.phone = phone.strip().replace('whatsapp:', '').lstrip('+')
        self._r = _get_redis()

    # ── Language preference ───────────────────────────────────────────────────

    def get_language(self) -> str | None:
        """Return stored language preference, or None if not set."""
        if not self._r:
            return self._db_get_language()
        try:
            return self._r.get(_LANG_KEY.format(phone=self.phone))
        except Exception as exc:
            logger.warning("[SessionStore] get_language failed: %s", exc)
            return None

    def set_language(self, lang: str) -> None:
        """Persist user's language preference."""
        if not self._r:
            self._db_set_language(lang)
            return
        try:
            self._r.setex(_LANG_KEY.format(phone=self.phone), LANG_TTL, lang)
        except Exception as exc:
            logger.warning("[SessionStore] set_language failed: %s", exc)

    # ── Session context (last intent) ─────────────────────────────────────────

    def get_last_intent(self) -> str | None:
        if not self._r:
            return None
        try:
            return self._r.get(_SESSION_KEY.format(phone=self.phone))
        except Exception:
            return None

    def set_last_intent(self, intent: str) -> None:
        if not self._r:
            return
        try:
            self._r.setex(_SESSION_KEY.format(phone=self.phone), SESSION_TTL, intent)
        except Exception:
            pass

    # ── Message counter ────────────────────────────────────────────────────────

    def increment_message_count(self) -> int:
        if not self._r:
            return 0
        try:
            key = _COUNT_KEY.format(phone=self.phone)
            count = self._r.incr(key)
            if count == 1:
                self._r.expire(key, LANG_TTL)
            return count
        except Exception:
            return 0

    # ── DB fallback ────────────────────────────────────────────────────────────
    # Uses the existing User model's language field when Redis is unavailable.

    def _db_get_language(self) -> str | None:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Strip country code for DB lookup if needed
            phone = self.phone.lstrip('91') if self.phone.startswith('91') else self.phone
            user = User.objects.filter(phone=phone).first()
            return getattr(user, 'language', None) if user else None
        except Exception:
            return None

    def _db_set_language(self, lang: str) -> None:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            phone = self.phone.lstrip('91') if self.phone.startswith('91') else self.phone
            User.objects.filter(phone=phone).update(language=lang)
        except Exception:
            pass
