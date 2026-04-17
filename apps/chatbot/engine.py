"""
apps/chatbot/engine.py

Central chat engine — orchestrates the full pipeline per message.

Pipeline:
    raw_message
        ↓ language_detector
        ↓ intent_classifier  (rule-based tree)
        ↓ state_machine      (FSM transition)
        ↓ response_engine    (rules + LLM)
        ↓ ChatMessage saved to DB
        ↓ response_text returned to caller
"""

import logging
import time
from django.utils import timezone

from .language_detector  import detect_language, normalize_lang
from .intent_classifier  import classify_intent
from .state_machine      import ConversationFSM, State, SLOT_REQUIRED_INTENTS
from .response_engine    import generate_response
from .models             import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

# LLM conversation history window (last N messages sent to LLM)
HISTORY_WINDOW = 10


def _get_or_create_session(session_id=None, user=None, phone='', channel='web') -> ChatSession:
    """Get active session or create a new one."""
    # Try to find existing active session
    if session_id:
        try:
            session = ChatSession.objects.get(pk=session_id)
            if session.is_active():
                return session
        except ChatSession.DoesNotExist:
            pass

    # Find recent active session for this user/phone
    qs = ChatSession.objects.filter(channel=channel, ended_at__isnull=True)
    if user and user.is_authenticated:
        qs = qs.filter(user=user)
    elif phone:
        qs = qs.filter(phone=phone)
    else:
        return _new_session(user, phone, channel)

    session = qs.order_by('-updated_at').first()
    if session and session.is_active():
        return session

    return _new_session(user, phone, channel)


def _new_session(user, phone, channel) -> ChatSession:
    session = ChatSession.objects.create(
        user    = user if (user and getattr(user, 'is_authenticated', False)) else None,
        phone   = phone,
        channel = channel,
        state   = 'idle',
        context = {},
    )
    logger.info("[Engine] New session created: %s", session.pk)
    return session


def _build_llm_history(session: ChatSession) -> list:
    """Build conversation history for LLM context window."""
    msgs = (
        ChatMessage.objects
        .filter(session=session, msg_type='text', role__in=['user', 'assistant'])
        .order_by('-created_at')[:HISTORY_WINDOW]
    )
    history = []
    for m in reversed(list(msgs)):
        history.append({'role': m.role, 'content': m.content})
    return history


def _save_message(session, role, content, intent='', lang='', confidence=0.0,
                  llm_used=False, tokens=0, latency=0):
    return ChatMessage.objects.create(
        session     = session,
        role        = role,
        content     = content,
        intent      = intent,
        language    = lang,
        confidence  = confidence,
        llm_used    = llm_used,
        tokens_used = tokens,
        latency_ms  = latency,
    )


def process_chat_message(
    raw_message:  str,
    session_id:   str   = None,
    user                = None,
    phone:        str   = '',
    channel:      str   = 'web',
) -> dict:
    """
    Full chatbot pipeline for one user message.

    Parameters
    ----------
    raw_message : User's raw text input
    session_id  : Existing session UUID (optional)
    user        : Django User instance (optional, for authenticated web users)
    phone       : Phone number for WhatsApp channel
    channel     : 'web' | 'whatsapp'

    Returns
    -------
    {
        'session_id': str,
        'response':   str,
        'intent':     str,
        'lang':       str,
        'state':      str,
        'llm_used':   bool,
    }
    """
    t0 = time.monotonic()

    # ── 1. Session ─────────────────────────────────────────────────────
    session = _get_or_create_session(session_id, user, phone, channel)

    # ── 2. Language detection ──────────────────────────────────────────
    detected_lang, conf = detect_language(raw_message)
    lang = normalize_lang(detected_lang)

    # Persist language to session
    if lang != session.language:
        session.language = lang
        session.save(update_fields=['language', 'updated_at'])

    # ── 3. Save user message ───────────────────────────────────────────
    _save_message(session, role='user', content=raw_message, lang=detected_lang)

    # ── 4. Intent classification ──────────────────────────────────────
    intent_result = classify_intent(raw_message, lang_code=detected_lang)
    logger.info("[Engine] Intent: %s (%.2f) | Lang: %s → %s",
                intent_result.intent, intent_result.confidence, detected_lang, lang)

    # ── 5. FSM transition ─────────────────────────────────────────────
    fsm = ConversationFSM(session)
    new_state, missing_slots = fsm.process_intent(intent_result.intent)
    fsm.set_current_intent(intent_result.intent)

    # ── 6. Slot collection mid-flight ─────────────────────────────────
    if missing_slots:
        # Ask for the first missing slot
        slot_key      = f'ask_slot_{missing_slots[0]}'
        slot_intent   = type(intent_result)(
            intent=slot_key, confidence=1.0, lang_hint=lang
        )
        response_text, llm_used, tokens, latency = generate_response(
            intent=slot_intent, lang=lang, user=user,
            conversation_history=[], session_context=session.context,
        )
    else:
        # ── 7. Build LLM history ───────────────────────────────────────
        history = _build_llm_history(session)

        # ── 8. Generate response ───────────────────────────────────────
        response_text, llm_used, tokens, latency = generate_response(
            intent=intent_result,
            lang=lang,
            user=user,
            conversation_history=history,
            session_context=session.context,
        )

        fsm.resolve()

    total_ms = int((time.monotonic() - t0) * 1000)

    # ── 9. Save assistant message ──────────────────────────────────────
    _save_message(
        session,
        role        = 'assistant',
        content     = response_text,
        intent      = intent_result.intent,
        lang        = lang,
        confidence  = intent_result.confidence,
        llm_used    = llm_used,
        tokens      = tokens,
        latency     = latency,
    )

    logger.info("[Engine] Done in %dms | LLM=%s | tokens=%d", total_ms, llm_used, tokens)

    return {
        'session_id': str(session.pk),
        'response':   response_text,
        'intent':     intent_result.intent,
        'lang':       lang,
        'state':      session.state,
        'llm_used':   llm_used,
        'latency_ms': total_ms,
    }
