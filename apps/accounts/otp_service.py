"""
apps/accounts/otp_service.py

Handles OTP generation, storage, and dispatch via Twilio SMS.
In OTP_TEST_MODE=True, always uses the code from OTP_TEST_CODE
and does NOT call Twilio — useful for development and demos.
"""
import random
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import OTPRecord

logger = logging.getLogger(__name__)


def generate_otp(mobile: str, purpose: str = 'register') -> str:
    """
    Generate a fresh OTP for a given mobile + purpose.

    - Marks any previous unverified OTPs for this mobile+purpose as expired.
    - In test mode returns OTP_TEST_CODE without calling Twilio.
    - Returns the 6-digit code string (for use in response/logging only in dev).
    """
    # Invalidate old OTPs for this mobile+purpose
    OTPRecord.objects.filter(
        mobile=mobile,
        purpose=purpose,
        verified=False,
    ).update(expires_at=timezone.now())

    # Generate code
    if settings.OTP_TEST_MODE:
        code = settings.OTP_TEST_CODE
    else:
        code = f"{random.randint(100000, 999999)}"

    expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    OTPRecord.objects.create(
        mobile=mobile,
        code=code,
        purpose=purpose,
        expires_at=expiry,
    )

    # Send OTP
    if settings.OTP_TEST_MODE:
        logger.info(f"[OTP TEST MODE] {mobile} → {code} (purpose={purpose})")
    else:
        _send_via_twilio(mobile, code)

    return code


def verify_otp(mobile: str, code: str, purpose: str = 'register') -> tuple[bool, str]:
    """
    Verify an OTP code.

    Returns (True, 'ok') on success.
    Returns (False, reason) on failure.
    reason is one of: 'not_found', 'expired', 'already_used', 'max_attempts', 'invalid'
    """
    try:
        record = OTPRecord.objects.filter(
            mobile=mobile,
            purpose=purpose,
            verified=False,
        ).latest('created_at')
    except OTPRecord.DoesNotExist:
        return False, 'not_found'

    # Increment attempts first
    record.attempts += 1
    record.save(update_fields=['attempts'])

    if record.attempts > 5:
        return False, 'max_attempts'

    if record.is_expired:
        return False, 'expired'

    if record.code != code.strip():
        return False, 'invalid'

    # Mark verified
    record.verified = True
    record.save(update_fields=['verified'])

    return True, 'ok'


def _send_via_twilio(mobile: str, code: str):
    """Send SMS via Twilio. Only called when OTP_TEST_MODE=False."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f"Your Nexura OTP is {code}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes. Do not share with anyone.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=f"+91{mobile.lstrip('+91').lstrip('0')}",
        )
        logger.info(f"[Twilio] OTP sent to {mobile}")
    except Exception as e:
        logger.error(f"[Twilio] Failed to send OTP to {mobile}: {e}")
        raise
