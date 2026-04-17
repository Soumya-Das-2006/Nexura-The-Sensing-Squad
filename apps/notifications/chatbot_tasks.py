"""
apps/notifications/chatbot_tasks.py

Celery tasks for the multilingual WhatsApp chatbot pipeline.

Separated from the main tasks.py to keep concerns clean.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.notifications.chatbot_tasks.process_chatbot_message',
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,         # task is acknowledged after completion, not on receipt
    reject_on_worker_lost=True,
)
def process_chatbot_message(payload: dict):
    """
    Main Celery task for the chatbot pipeline.

    Receives the raw Twilio POST payload, runs the full
    language-detect → intent-detect → respond pipeline,
    and sends the reply via Twilio WhatsApp API.

    Parameters
    ----------
    payload : dict with keys From, Body, MessageSid etc.

    Retry policy:
        Retried up to 3 times on transient failures (network, DB timeout).
        Each retry waits 10 seconds before re-attempting.
    """
    from apps.notifications.chatbot.pipeline import (
        parse_twilio_payload,
        process_message,
    )

    try:
        parsed = parse_twilio_payload(payload)
        if parsed is None:
            logger.warning("[ChatbotTask] Could not parse payload: %s", payload)
            return  # don't retry bad payloads

        sender_phone, message_text = parsed

        if not message_text.strip():
            logger.info("[ChatbotTask] Empty message from %s — skipping.", sender_phone)
            return

        success = process_message(
            sender_phone=sender_phone,
            message_text=message_text,
        )

        if not success:
            raise Exception(f"Failed to send reply to {sender_phone}")

    except Exception as exc:
        logger.error("[ChatbotTask] Error: %s", exc, exc_info=True)
        raise process_chatbot_message.retry(exc=exc)
