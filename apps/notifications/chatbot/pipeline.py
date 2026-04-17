"""
apps/notifications/chatbot/pipeline.py

Main chatbot processing pipeline.

Flow:
    incoming message
        ↓
    parse_twilio_payload()         — extract text + sender phone
        ↓
    SessionStore.get_language()    — check stored language preference
        ↓
    language_detector.detect()     — detect language from text
        ↓
    normalize_lang()               — map hi_en → hi etc.
        ↓
    SessionStore.set_language()    — persist detected language
        ↓
    intent_detector.detect()       — detect intent
        ↓
    context_builder.build()        — fetch DB data for placeholders
        ↓
    responses.get_response()       — render response text
        ↓
    twilio_sender.send()           — deliver via Twilio WhatsApp API
"""

import logging
from typing import Optional

from .language_detector import detect_language, normalize_lang
from .intent_detector    import detect_intent
from .responses          import get_response
from .context_builder    import build_context, get_user_by_phone
from .session_store      import SessionStore
from .twilio_sender      import send_whatsapp

logger = logging.getLogger(__name__)


def parse_twilio_payload(payload: dict) -> Optional[tuple[str, str]]:
    """
    Extract (sender_phone, message_text) from a Twilio WhatsApp webhook payload.

    Twilio sends a form-encoded POST, but our webhook view converts it to a dict.
    Expected keys: 'From', 'Body'

    Returns None if required fields are missing.
    """
    sender = payload.get('From') or payload.get('from')
    body   = payload.get('Body') or payload.get('body') or ''

    if not sender:
        logger.warning("[Pipeline] Missing 'From' field in Twilio payload.")
        return None

    # 'From' is already in 'whatsapp:+91XXXXXXXXXX' format
    return (sender.strip(), body.strip())


def process_message(sender_phone: str, message_text: str) -> bool:
    """
    Full chatbot pipeline for a single incoming message.

    Parameters
    ----------
    sender_phone : 'whatsapp:+91XXXXXXXXXX' (as received from Twilio)
    message_text : Raw message body

    Returns
    -------
    True if reply was sent successfully, False otherwise.
    """
    logger.info("[Pipeline] Processing message from %s: %r", sender_phone, message_text[:80])

    # ── 1. Session store init ─────────────────────────────────────────────────
    session = SessionStore(phone=sender_phone)
    session.increment_message_count()

    # ── 2. Language detection ─────────────────────────────────────────────────
    stored_lang = session.get_language()

    # Always detect from current message (detects language switches mid-session)
    detected_lang, confidence = detect_language(message_text)
    canonical_lang = normalize_lang(detected_lang)

    # Use stored preference if detection confidence is low
    if confidence < 0.55 and stored_lang:
        lang = stored_lang
        logger.debug("[Pipeline] Low confidence (%.2f), using stored lang: %s", confidence, lang)
    else:
        lang = canonical_lang
        # Persist new / updated language preference
        if lang != stored_lang:
            session.set_language(lang)
            logger.info("[Pipeline] Language preference updated: %s → %s", stored_lang, lang)

    logger.info("[Pipeline] Language: %s (detected=%s, confidence=%.2f)", lang, detected_lang, confidence)

    # ── 3. Intent detection ───────────────────────────────────────────────────
    intent = detect_intent(text=message_text, lang_code=detected_lang)
    logger.info("[Pipeline] Intent: %s (confidence=%.2f)", intent.name, intent.confidence)
    session.set_last_intent(intent.name)

    # ── 4. Load user from DB ──────────────────────────────────────────────────
    user = get_user_by_phone(sender_phone)
    if user:
        logger.debug("[Pipeline] User found: %s (id=%s)", user.get_full_name(), user.pk)
    else:
        logger.debug("[Pipeline] No user found for %s — using guest context.", sender_phone)

    # ── 5. Build response context ─────────────────────────────────────────────
    context = build_context(intent_name=intent.name, user=user)

    # ── 6. Render response ────────────────────────────────────────────────────
    response_text = get_response(intent_name=intent.name, lang=lang, **context)
    logger.debug("[Pipeline] Response text:\n%s", response_text[:300])

    # ── 7. Send via Twilio ────────────────────────────────────────────────────
    success = send_whatsapp(to=sender_phone, body=response_text)

    if success:
        logger.info("[Pipeline] Reply sent to %s for intent '%s'.", sender_phone, intent.name)
    else:
        logger.error("[Pipeline] Failed to send reply to %s.", sender_phone)

    return success
