"""
apps/notifications/channels.py

Three notification channels used by Nexura:

1. WhatsApp  — Meta Cloud API (primary channel for workers)
2. Email     — SendGrid (secondary / admin alerts)
3. SMS       — Twilio (OTP fallback only — OTP is handled in accounts.otp_service)

All functions check for missing credentials and log rather than raise,
so a missing API key never crashes the main pipeline.

Language support
----------------
WhatsApp message bodies are built in the worker's preferred language.
Supported: en, hi, mr, bn, ta, te
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── WhatsApp Cloud API ───────────────────────────────────────────────────────

class WhatsAppClient:
    """
    Meta WhatsApp Business Cloud API v17.0
    Sends text messages to Indian mobile numbers.
    """

    BASE_URL = "https://graph.facebook.com/v17.0/{phone_id}/messages"

    def __init__(self):
        self.token    = settings.WHATSAPP_TOKEN
        self.phone_id = settings.WHATSAPP_PHONE_ID

    def _is_configured(self) -> bool:
        return bool(self.token and self.phone_id)

    def send_text(self, to_mobile: str, body: str) -> bool:
        """
        Send a plain text WhatsApp message.

        Parameters
        ----------
        to_mobile : 10-digit Indian number (without +91)
        body      : Message text (max 4096 chars)

        Returns True on success.
        """
        if not self._is_configured():
            logger.info("[WhatsApp MOCK] To: +91%s | %s", to_mobile, body[:80])
            return True   # treat as success in dev

        to = f"91{to_mobile.lstrip('+').lstrip('91').lstrip('0')}"
        url = self.BASE_URL.format(phone_id=self.phone_id)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type":    "individual",
            "to":                to,
            "type":              "text",
            "text":              {"preview_url": False, "body": body},
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            logger.info("[WhatsApp] Sent to +91%s", to_mobile)
            return True
        except requests.RequestException as exc:
            logger.error("[WhatsApp] Send failed to +91%s: %s", to_mobile, exc)
            return False

    def send_webhook_verification(self, mode: str, challenge: str, verify_token: str) -> bool:
        """Verify incoming webhook subscription from Meta."""
        return (
            mode == "subscribe"
            and verify_token == settings.WHATSAPP_VERIFY_TOKEN
        )


# ─── SendGrid Email ───────────────────────────────────────────────────────────

class EmailClient:
    """SendGrid transactional email sender."""

    def __init__(self):
        self.api_key   = settings.SENDGRID_API_KEY
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    def send(self, to_email: str, subject: str, html_body: str,
             plain_body: str = '') -> bool:
        """Send a transactional email via SendGrid."""
        if not self._is_configured():
            logger.info("[Email MOCK] To: %s | Subject: %s", to_email, subject)
            return True

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Content

            message = Mail(
                from_email = self.from_email,
                to_emails  = to_email,
                subject    = subject,
            )
            message.add_content(Content("text/html",  html_body))
            if plain_body:
                message.add_content(Content("text/plain", plain_body))

            sg   = SendGridAPIClient(self.api_key)
            resp = sg.send(message)

            if resp.status_code in (200, 202):
                logger.info("[Email] Sent to %s: %s", to_email, subject)
                return True
            else:
                logger.warning("[Email] Unexpected status %s for %s", resp.status_code, to_email)
                return False

        except Exception as exc:
            logger.error("[Email] Send failed to %s: %s", to_email, exc)
            return False


# ─── Multilingual WhatsApp messages ──────────────────────────────────────────

MESSAGES = {
    # ── Claim approved ────────────────────────────────────────────────────
    'claim_approved': {
        'en': (
            "✅ *Nexura Claim Approved!*\n\n"
            "Your claim of ₹{amount} has been approved.\n"
            "Trigger: {trigger}\n"
            "Zone: {zone}\n\n"
            "💰 UPI payout of ₹{amount} is being processed to {upi_id}.\n"
            "You'll receive it within 2 hours.\n\n"
            "_Claim #{claim_id} | Nexura_"
        ),
        'hi': (
            "✅ *Nexura दावा स्वीकृत!*\n\n"
            "आपका ₹{amount} का दावा मंजूर हो गया है।\n"
            "कारण: {trigger}\n"
            "क्षेत्र: {zone}\n\n"
            "💰 ₹{amount} का UPI भुगतान {upi_id} पर भेजा जा रहा है।\n"
            "2 घंटे के अंदर मिल जाएगा।\n\n"
            "_दावा #{claim_id} | Nexura_"
        ),
        'mr': (
            "✅ *Nexura दावा मंजूर!*\n\n"
            "तुमचा ₹{amount} चा दावा मंजूर झाला आहे।\n"
            "कारण: {trigger}\n\n"
            "💰 ₹{amount} UPI वर {upi_id} ला पाठवले जात आहे।\n"
            "2 तासांत मिळेल।\n\n"
            "_दावा #{claim_id} | Nexura_"
        ),
        'ta': (
            "✅ *Nexura கோரிக்கை அங்கீகரிக்கப்பட்டது!*\n\n"
            "உங்கள் ₹{amount} கோரிக்கை அங்கீகரிக்கப்பட்டது.\n"
            "காரணம்: {trigger}\n\n"
            "💰 ₹{amount} உங்கள் UPI {upi_id} க்கு அனுப்பப்படுகிறது.\n"
            "2 மணி நேரத்தில் கிடைக்கும்.\n\n"
            "_கோரிக்கை #{claim_id} | Nexura_"
        ),
        'te': (
            "✅ *Nexura క్లెయిమ్ ఆమోదించబడింది!*\n\n"
            "మీ ₹{amount} క్లెయిమ్ ఆమోదించబడింది.\n"
            "కారణం: {trigger}\n\n"
            "💰 ₹{amount} మీ UPI {upi_id} కు పంపబడుతోంది.\n"
            "2 గంటల్లో వస్తుంది.\n\n"
            "_క్లెయిమ్ #{claim_id} | Nexura_"
        ),
        'bn': (
            "✅ *Nexura দাবি অনুমোদিত!*\n\n"
            "আপনার ₹{amount} এর দাবি অনুমোদিত হয়েছে।\n"
            "কারণ: {trigger}\n\n"
            "💰 ₹{amount} আপনার UPI {upi_id} তে পাঠানো হচ্ছে।\n"
            "২ ঘণ্টার মধ্যে পাবেন।\n\n"
            "_দাবি #{claim_id} | Nexura_"
        ),
    },

    # ── Claim under review ────────────────────────────────────────────────
    'claim_under_review': {
        'en': (
            "🔍 *Nexura Claim Under Review*\n\n"
            "Your claim of ₹{amount} is being reviewed by our team.\n"
            "Claim #{claim_id}\n\n"
            "We'll update you within 24 hours. Questions? Reply to this message."
        ),
        'hi': (
            "🔍 *Nexura दावा समीक्षा में*\n\n"
            "आपका ₹{amount} का दावा हमारी टीम देख रही है।\n"
            "दावा #{claim_id}\n\n"
            "24 घंटे में जवाब देंगे।"
        ),
    },

    # ── Claim rejected ────────────────────────────────────────────────────
    'claim_rejected': {
        'en': (
            "❌ *Nexura Claim Not Approved*\n\n"
            "Your claim #{claim_id} of ₹{amount} was not approved.\n"
            "Reason: {reason}\n\n"
            "If you believe this is an error, contact our support team."
        ),
        'hi': (
            "❌ *Nexura दावा अस्वीकृत*\n\n"
            "आपका दावा #{claim_id} (₹{amount}) मंजूर नहीं हुआ।\n"
            "कारण: {reason}\n\n"
            "गलती लगे तो सपोर्ट से संपर्क करें।"
        ),
    },

    # ── Payout credited ───────────────────────────────────────────────────
    'payout_credited': {
        'en': (
            "💸 *Money Received — Nexura*\n\n"
            "₹{amount} has been credited to your UPI {upi_id}.\n"
            "UTR: {utr}\n"
            "Time: {time}\n\n"
            "Thank you for trusting Nexura. Stay safe! 🙏"
        ),
        'hi': (
            "💸 *पैसे मिल गए — Nexura*\n\n"
            "₹{amount} आपके UPI {upi_id} में आ गए।\n"
            "UTR: {utr}\n"
            "समय: {time}\n\n"
            "Nexura पर भरोसा रखने के लिए शुक्रिया! 🙏"
        ),
        'mr': (
            "💸 *पैसे मिळाले — Nexura*\n\n"
            "₹{amount} तुमच्या UPI {upi_id} मध्ये जमा झाले.\n"
            "UTR: {utr}\n\n"
            "Nexura वर विश्वास ठेवल्याबद्दल धन्यवाद! 🙏"
        ),
        'ta': (
            "💸 *பணம் வந்தது — Nexura*\n\n"
            "₹{amount} உங்கள் UPI {upi_id} க்கு வரவு வைக்கப்பட்டது.\n"
            "UTR: {utr}\n\n"
            "நன்றி! 🙏"
        ),
        'te': (
            "💸 *డబ్బు వచ్చింది — Nexura*\n\n"
            "₹{amount} మీ UPI {upi_id} కు జమ చేయబడింది.\n"
            "UTR: {utr}\n\n"
            "ధన్యవాదాలు! 🙏"
        ),
        'bn': (
            "💸 *টাকা এসেছে — Nexura*\n\n"
            "₹{amount} আপনার UPI {upi_id}-তে জমা হয়েছে।\n"
            "UTR: {utr}\n\n"
            "ধন্যবাদ! 🙏"
        ),
    },

    # ── Payout failed ─────────────────────────────────────────────────────
    'payout_failed': {
        'en': (
            "⚠️ *Nexura Payout Failed*\n\n"
            "We couldn't transfer ₹{amount} to your UPI {upi_id}.\n"
            "Reason: {reason}\n\n"
            "Please update your UPI ID or contact support. We'll retry shortly."
        ),
        'hi': (
            "⚠️ *Nexura भुगतान विफल*\n\n"
            "₹{amount} आपके UPI {upi_id} में नहीं भेज पाए।\n"
            "कारण: {reason}\n\n"
            "कृपया अपना UPI ID अपडेट करें या सपोर्ट से संपर्क करें।"
        ),
    },

    # ── Payment captured (weekly premium) ────────────────────────────────
    'payment_captured': {
        'en': (
            "✅ *Nexura Weekly Premium*\n\n"
            "₹{amount} has been successfully collected for this week's coverage.\n"
            "You're protected until next Sunday. Stay safe!"
        ),
        'hi': (
            "✅ *Nexura साप्ताहिक प्रीमियम*\n\n"
            "इस हफ्ते के कवरेज के लिए ₹{amount} कट गया।\n"
            "अगले रविवार तक आप सुरक्षित हैं!"
        ),
    },

    # ── Payment failed ────────────────────────────────────────────────────
    'payment_failed': {
        'en': (
            "⚠️ *Nexura Premium Collection Failed*\n\n"
            "We couldn't collect this week's premium.\n"
            "Reason: {reason}\n\n"
            "Please ensure your bank account has sufficient balance.\n"
            "Your policy may be paused if payment fails again."
        ),
        'hi': (
            "⚠️ *Nexura प्रीमियम विफल*\n\n"
            "इस हफ्ते का प्रीमियम नहीं कट पाया।\n"
            "कारण: {reason}\n\n"
            "बैंक अकाउंट में पैसे सुनिश्चित करें।"
        ),
    },

    # ── Grace token used ──────────────────────────────────────────────────
    'grace_used': {
        'en': (
            "🎁 *Nexura Grace Token Used*\n\n"
            "Your payment failed this week, but we've applied your grace token.\n"
            "Your policy remains active.\n\n"
            "⚠️ You have no more grace tokens this year. "
            "A future payment failure will pause your policy."
        ),
        'hi': (
            "🎁 *Nexura ग्रेस टोकन उपयोग*\n\n"
            "इस हफ्ते का भुगतान विफल रहा, लेकिन हमने आपका ग्रेस टोकन लगाया।\n"
            "पॉलिसी चालू है।\n\n"
            "⚠️ इस साल अब कोई ग्रेस टोकन नहीं बचा।"
        ),
    },

    # ── Forecast alert ────────────────────────────────────────────────────
    'forecast': {
        'en': (
            "🌦️ *Nexura Weekly Risk Forecast*\n\n"
            "*{zone}* — Week of {week}\n\n"
            "☔ Rain risk: {rain}%\n"
            "🌡️ Heat risk: {heat}%\n"
            "🌫️ AQI risk:  {aqi}%\n"
            "⚡ Overall:   *{level}*\n\n"
            "{advice}\n\n"
            "_Powered by Facebook Prophet · Nexura_"
        ),
        'hi': (
            "🌦️ *Nexura साप्ताहिक जोखिम पूर्वानुमान*\n\n"
            "*{zone}* — {week} का सप्ताह\n\n"
            "☔ बारिश जोखिम: {rain}%\n"
            "🌡️ गर्मी जोखिम: {heat}%\n"
            "🌫️ AQI जोखिम:  {aqi}%\n"
            "⚡ कुल जोखिम:  *{level}*\n\n"
            "{advice}"
        ),
    },

    # ── Premium updated ───────────────────────────────────────────────────
    'premium_updated': {
        'en': (
            "📊 *Nexura Premium Update*\n\n"
            "Your weekly premium has been recalculated.\n"
            "Old: ₹{old}/week → New: ₹{new}/week\n"
            "Risk score: {risk:.2f}\n\n"
            "The change takes effect next Monday."
        ),
        'hi': (
            "📊 *Nexura प्रीमियम अपडेट*\n\n"
            "आपका साप्ताहिक प्रीमियम बदला है।\n"
            "पुराना: ₹{old}/सप्ताह → नया: ₹{new}/सप्ताह\n\n"
            "यह बदलाव अगले सोमवार से लागू होगा।"
        ),
    },
}


def get_message(event_type: str, language: str, **kwargs) -> str:
    """
    Get a localised message template and format it with the provided kwargs.
    Falls back to English if the language is not supported.
    """
    templates = MESSAGES.get(event_type, {})
    template  = templates.get(language) or templates.get('en', '')
    if not template:
        logger.warning("[notifications] No template for event=%s lang=%s", event_type, language)
        return ''
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning("[notifications] Missing key %s in template %s", e, event_type)
        return template


# ─── Email HTML templates (minimal inline styles) ─────────────────────────────

def build_email_html(title: str, body_html: str) -> str:
    """Wrap body_html in a minimal Nexura-branded email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:Inter,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr style="background:#015fc9;border-radius:12px 12px 0 0;">
          <td style="padding:24px 32px;color:#fff;font-size:22px;font-weight:700;">
            🛡️ Nexura
          </td>
        </tr>
        <!-- Body -->
        <tr><td style="padding:32px;color:#1e293b;font-size:15px;line-height:1.7;">
          {body_html}
        </td></tr>
        <!-- Footer -->
        <tr><td style="padding:20px 32px;border-top:1px solid #e2e8f0;
                       color:#94a3b8;font-size:12px;">
          Nexura · Income Protection for India's Gig Workers ·
          <a href="https://nexaura.in" style="color:#015fc9;">nexaura.in</a><br>
          Built for Guidewire DEVTrails 2026
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─── Singleton instances ──────────────────────────────────────────────────────

whatsapp = WhatsAppClient()
email    = EmailClient()
