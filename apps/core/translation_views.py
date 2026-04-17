"""
apps/core/translation_views.py
──────────────────────────────
Translation API endpoint for the Nexura multilingual system.

POST /translate/
Body : { "target_lang": "hi", "texts": ["Hello", "Welcome"] }
Return: { "translations": ["नमस्ते", "स्वागत है"], "provider": "mymemory", "cached": 1 }

Provider fallback chain:
  1. MyMemory       – free, no key, 1 000 words/day/IP
  2. LibreTranslate – public demo mirror
  3. Google (unofficial) – translate.googleapis.com, no key
  4. Graceful degradation – return original text
"""

import hashlib
import json
import logging
import concurrent.futures
from urllib.parse import quote

import requests
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_LANGS = {
    "en", "hi", "gu", "bn", "ta", "te",
    "mr", "kn", "ml", "pa", "ur", "or", "as",
}

# MyMemory uses slightly different codes for some langs
MYMEMORY_LANG_MAP = {
    "or": "or",   # Odia
    "as": "as",   # Assamese
    "pa": "pa",   # Punjabi
}

# LibreTranslate public instance (fallback)
LIBRETRANSLATE_URLS = [
    "https://libretranslate.de/translate",
    "https://translate.argosopentech.com/translate",
]

MAX_TEXTS          = 50       # per request
MAX_TEXT_LENGTH    = 500      # chars per text item
CACHE_TTL          = 60 * 60 * 24 * 7  # 7 days
PROVIDER_TIMEOUT   = 8        # seconds
MAX_WORKERS        = 6        # thread pool size


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_key(lang: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"translate:{lang}:{digest}"


def _load_from_cache(lang: str, texts: list[str]) -> dict[str, str]:
    """Return {original_text: translated_text} for all cache hits."""
    keys = {_cache_key(lang, t): t for t in texts}
    hits = cache.get_many(list(keys.keys()))
    return {keys[k]: v for k, v in hits.items()}


def _save_to_cache(lang: str, mapping: dict[str, str]) -> None:
    """Persist {original: translated} into the cache."""
    to_set = {_cache_key(lang, src): tgt for src, tgt in mapping.items()}
    try:
        cache.set_many(to_set, CACHE_TTL)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Translation cache write failed: %s", exc)


# ── Provider: MyMemory ────────────────────────────────────────────────────────

def _translate_mymemory(texts: list[str], target_lang: str) -> list[str] | None:
    """
    Translate via MyMemory REST API (free tier, batch one-by-one via threads).
    Docs: https://mymemory.translated.net/doc/spec.php
    """
    lang_pair = f"en|{target_lang}"

    def _single(text: str) -> str:
        try:
            url = (
                f"https://api.mymemory.translated.net/get"
                f"?q={quote(text)}&langpair={lang_pair}"
            )
            resp = requests.get(url, timeout=PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if translated and translated.upper() != text.upper():
                return translated
            # Fallback within response: first match
            matches = data.get("matches", [])
            if matches:
                return matches[0].get("translation", text)
            return text
        except Exception:  # noqa: BLE001
            return text

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            results = list(pool.map(_single, texts, timeout=PROVIDER_TIMEOUT + 5))
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("MyMemory batch failed: %s", exc)
        return None


# ── Provider: LibreTranslate ──────────────────────────────────────────────────

def _translate_libretranslate(texts: list[str], target_lang: str) -> list[str] | None:
    """
    LibreTranslate public demo instances — tries each mirror in order.
    NOTE: Some mirrors require an API key; we skip those gracefully.
    """
    for base_url in LIBRETRANSLATE_URLS:
        try:
            results = []
            for text in texts:
                payload = {
                    "q":      text,
                    "source": "en",
                    "target": target_lang,
                    "format": "text",
                }
                resp = requests.post(
                    base_url,
                    json=payload,
                    timeout=PROVIDER_TIMEOUT,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 403:
                    # Key required on this mirror — skip
                    break
                resp.raise_for_status()
                data = resp.json()
                results.append(data.get("translatedText", text))

            if len(results) == len(texts):
                return results
        except Exception as exc:  # noqa: BLE001
            logger.debug("LibreTranslate mirror %s failed: %s", base_url, exc)
            continue

    return None


# ── Provider: Google (unofficial) ────────────────────────────────────────────

def _translate_google_unofficial(texts: list[str], target_lang: str) -> list[str] | None:
    """
    Uses the public client-API endpoint used by Android / browser Google Translate.
    No API key required; subject to rate-limiting.
    """
    try:
        # Build a combined request (single call, texts joined with |||)
        results = []
        for text in texts:
            url = (
                "https://translate.googleapis.com/translate_a/single"
                f"?client=gtx&sl=en&tl={target_lang}&dt=t&q={quote(text)}"
            )
            resp = requests.get(url, timeout=PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # Response format: [[[translated, original, ...], ...], ...]
            translated_parts = data[0]
            translated = "".join(
                part[0] for part in translated_parts if part and part[0]
            )
            results.append(translated or text)
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google unofficial translate failed: %s", exc)
        return None


# ── Core translate router ─────────────────────────────────────────────────────

def translate_texts(texts: list[str], target_lang: str) -> dict:
    """
    Translate a list of texts to *target_lang*.
    Returns {"translations": [...], "provider": str, "cached": int}
    """
    # 1. Cache look-up
    cached_map = _load_from_cache(target_lang, texts)
    cached_count = len(cached_map)

    missing = [t for t in texts if t not in cached_map]

    provider_used = "cache"
    fresh_map: dict[str, str] = {}

    if missing:
        # 2. Try providers in order
        for provider_fn, provider_name in [
            (_translate_mymemory,            "mymemory"),
            (_translate_libretranslate,      "libretranslate"),
            (_translate_google_unofficial,   "google"),
        ]:
            result = provider_fn(missing, target_lang)
            if result and len(result) == len(missing):
                fresh_map = dict(zip(missing, result))
                provider_used = provider_name
                break
        else:
            # All providers failed → return originals
            fresh_map = {t: t for t in missing}
            provider_used = "fallback"

        _save_to_cache(target_lang, fresh_map)

    # 3. Merge cache + fresh, preserve order
    combined = {**cached_map, **fresh_map}
    ordered = [combined.get(t, t) for t in texts]

    return {
        "translations": ordered,
        "provider":     provider_used,
        "cached":       cached_count,
    }


# ── View ──────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class TranslateView(View):
    """
    POST /translate/

    Accepts JSON body, returns JSON response.
    CSRF is exempt here because the JS client always sends the csrftoken header,
    but this endpoint is also usable server-to-server / from Postman for testing.
    """

    def post(self, request, *args, **kwargs):
        # ── Parse body ────────────────────────────────────────────────────────
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"error": "Invalid JSON body."}, status=400)

        target_lang = body.get("target_lang", "").strip().lower()
        texts       = body.get("texts", [])

        # ── Validate ───────────────────────────────────────────────────────────
        if not target_lang or target_lang not in SUPPORTED_LANGS:
            return JsonResponse(
                {"error": f"Unsupported target_lang: '{target_lang}'."},
                status=400,
            )

        if not isinstance(texts, list) or not texts:
            return JsonResponse({"error": "'texts' must be a non-empty list."}, status=400)

        if len(texts) > MAX_TEXTS:
            return JsonResponse(
                {"error": f"Maximum {MAX_TEXTS} texts per request."},
                status=400,
            )

        # Sanitise each text
        clean_texts = []
        for item in texts:
            if not isinstance(item, str):
                clean_texts.append(str(item))
            else:
                clean_texts.append(item[:MAX_TEXT_LENGTH])

        # English → return as-is (no translation needed)
        if target_lang == "en":
            return JsonResponse({"translations": clean_texts, "provider": "passthrough", "cached": 0})

        # ── Translate ──────────────────────────────────────────────────────────
        try:
            result = translate_texts(clean_texts, target_lang)
            return JsonResponse(result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Translation error: %s", exc)
            return JsonResponse(
                {"translations": clean_texts, "fallback": True, "error": "Translation service unavailable."},
                status=200,  # Return 200 with originals so JS client degrades gracefully
            )

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {"message": "POST to this endpoint with target_lang and texts."},
            status=405,
        )
