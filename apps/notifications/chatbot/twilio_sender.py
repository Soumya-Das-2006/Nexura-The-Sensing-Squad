"""
apps/notifications/chatbot/twilio_sender.py

Twilio WhatsApp messaging service for Nexura chatbot.

Uses Twilio's WhatsApp Sandbox (or production number) to send
replies to incoming user messages.

Configuration (in .env):
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=your_auth_token
    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # Sandbox number
    # OR for production:
    TWILIO_WHATSAPP_FROM=whatsapp:+91XXXXXXXXXX  # Your approved number

The sender gracefully degrades to LOG-ONLY mode when credentials are
missing — safe for local dev and CI.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TwilioWhatsAppSender:
    """
    Wraps Twilio REST client for WhatsApp message delivery.

    Usage:
        sender = TwilioWhatsAppSender()
        sender.send(to="+919876543210", body="Hello!")
    """

    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token  = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

    def _is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token)

    def send(self, to: str, body: str) -> bool:
        """
        Send a WhatsApp message via Twilio.

        Parameters
        ----------
        to   : Recipient phone number in E.164 format (e.g. '+919876543210')
               Can also include 'whatsapp:' prefix — it will be normalized.
        body : Message text (max 1600 chars for WhatsApp via Twilio)

        Returns
        -------
        True if sent successfully, False otherwise.
        """
        # Normalize 'to' number
        to_number = to.strip()
        if not to_number.startswith('whatsapp:'):
            # Ensure E.164 format
            digits = ''.join(filter(str.isdigit, to_number))
            if len(digits) == 10:           # Indian number without country code
                digits = '91' + digits
            to_number = f'whatsapp:+{digits}'

        if not self._is_configured():
            logger.info(
                "[TwilioSender MOCK] Would send to %s:\n%s",
                to_number, body[:200]
            )
            return True   # treat as success in dev/test

        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)

            message = client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number,
            )
            logger.info(
                "[TwilioSender] Sent to %s | SID: %s | Status: %s",
                to_number, message.sid, message.status
            )
            return True

        except Exception as exc:
            logger.error(
                "[TwilioSender] Failed to send to %s: %s",
                to_number, exc, exc_info=True
            )
            return False


# Module-level singleton — one client per worker process
_sender = None


def get_sender() -> TwilioWhatsAppSender:
    global _sender
    if _sender is None:
        _sender = TwilioWhatsAppSender()
    return _sender


def send_whatsapp(to: str, body: str) -> bool:
    """Convenience function — use this in tasks."""
    return get_sender().send(to=to, body=body)
