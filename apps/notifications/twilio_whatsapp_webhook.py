"""
apps/notifications/twilio_whatsapp_webhook.py

Twilio WhatsApp webhook view.

Twilio sends an HTTP POST (form-encoded) for each incoming WhatsApp message.
We immediately acknowledge with 200 OK and queue async processing via Celery.

Endpoint: POST /api/v1/whatsapp/webhook/twilio/

Twilio configuration:
    - Go to: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
    - Set webhook URL to: https://your-domain.com/api/v1/whatsapp/webhook/twilio/
    - Method: HTTP POST

Request parameters from Twilio:
    From        → whatsapp:+919876543210  (sender)
    To          → whatsapp:+14155238886   (your Twilio sandbox/prod number)
    Body        → message text
    MessageSid  → unique message ID
    NumMedia    → number of attachments (0 for text)

Signature validation:
    Set TWILIO_AUTH_TOKEN in .env — validation is active when DEBUG=False.
    In production, Twilio signs every request to prevent spoofing.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


def _validate_twilio_signature(request) -> bool:
    """
    Validate Twilio request signature in production.
    Skip validation in DEBUG mode or if TWILIO_VALIDATE_WEBHOOK=False.
    """
    if settings.DEBUG:
        return True

    validate = getattr(settings, 'TWILIO_VALIDATE_WEBHOOK', True)
    if not validate:
        return True

    try:
        from twilio.request_validator import RequestValidator
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        if not auth_token:
            logger.warning("[TwilioWebhook] No TWILIO_AUTH_TOKEN — skipping validation.")
            return True

        validator = RequestValidator(auth_token)
        url = request.build_absolute_uri()
        signature = request.headers.get('X-Twilio-Signature', '')
        # POST params as dict
        params = {k: v for k, v in request.POST.items()}
        valid = validator.validate(url, params, signature)
        if not valid:
            logger.warning("[TwilioWebhook] Invalid Twilio signature from %s", request.META.get('REMOTE_ADDR'))
        return valid
    except Exception as exc:
        logger.error("[TwilioWebhook] Signature validation error: %s", exc)
        return True   # fail-open to avoid blocking legitimate traffic on misconfiguration


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWhatsAppWebhookView(View):
    """
    Handles incoming WhatsApp messages from Twilio.
    """

    def post(self, request):
        """Receive incoming message and queue for async processing."""

        # 1. Validate Twilio signature
        if not _validate_twilio_signature(request):
            return HttpResponse('Forbidden', status=403)

        # 2. Extract payload (Twilio sends form-encoded, not JSON)
        payload = {
            'From':       request.POST.get('From', ''),
            'To':         request.POST.get('To', ''),
            'Body':       request.POST.get('Body', ''),
            'MessageSid': request.POST.get('MessageSid', ''),
            'NumMedia':   request.POST.get('NumMedia', '0'),
        }

        logger.info(
            "[TwilioWebhook] Incoming from=%s body=%r sid=%s",
            payload['From'], payload['Body'][:80], payload['MessageSid']
        )

        # 3. Ignore media-only messages gracefully
        if payload['NumMedia'] != '0' and not payload['Body'].strip():
            # Send a friendly text-only reply
            payload['Body'] = 'image'  # will match 'unknown' intent → help menu

        # 4. Queue Celery task (returns 200 immediately — Twilio needs fast ACK)
        try:
            from apps.notifications.chatbot_tasks import process_chatbot_message
            process_chatbot_message.delay(payload)
        except Exception as exc:
            logger.error("[TwilioWebhook] Failed to queue Celery task: %s", exc, exc_info=True)
            # Still return 200 to Twilio so it doesn't retry
            return HttpResponse('QUEUING_ERROR', status=200)

        # Twilio accepts any 200 response — empty body is fine
        return HttpResponse('OK', status=200)

    def get(self, request):
        """Health check for webhook URL."""
        return HttpResponse('Twilio WhatsApp Webhook Active', status=200)
