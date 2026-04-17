"""
apps/accounts/kyc_service.py

Two-step KYC verification service.

Step 1 — request_kyc_otp(user)  → sends OTP to worker's mobile
Step 2 — verify_kyc_otp(user, otp) → verifies OTP, marks KYC verified

Currently uses mock OTP (prints to console / sends via existing SMS service).
To switch to real UIDAI DigiLocker API, replace _send_uidai_otp() only.
"""
import logging
import random
import string
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_LENGTH    = 6
OTP_TTL_SECS  = 600   # 10 minutes
CACHE_PREFIX  = "kyc_otp:"


# ── OTP helpers ───────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def _cache_key(mobile: str) -> str:
    return f"{CACHE_PREFIX}{mobile}"


def _store_otp(mobile: str, otp: str) -> None:
    cache.set(_cache_key(mobile), otp, timeout=OTP_TTL_SECS)


def _get_stored_otp(mobile: str) -> str | None:
    return cache.get(_cache_key(mobile))


def _clear_otp(mobile: str) -> None:
    cache.delete(_cache_key(mobile))


# ── SMS delivery ──────────────────────────────────────────────────────────────

def _send_otp_sms(mobile: str, otp: str) -> bool:
    """
    Send OTP via existing SMS service (Twilio/SNS).
    Falls back to console log in DEBUG mode.
    """
    from django.conf import settings

    message = f"Your Nexura KYC verification OTP is {otp}. Valid for 10 minutes. Do not share."

    if settings.DEBUG:
        # Console output in development
        print(f"\n{'='*50}")
        print(f"[KYC OTP] Mobile: {mobile}")
        print(f"[KYC OTP] OTP: {otp}")
        print(f"{'='*50}\n")
        logger.info("[kyc] DEBUG mode — OTP for %s: %s", mobile, otp)
        return True

    # ── Production: use existing OTP service ─────────────────────────────
    try:
        from apps.accounts.otp_service import send_sms
        send_sms(mobile, message)
        return True
    except Exception as exc:
        logger.error("[kyc] SMS send failed for %s: %s", mobile, exc)
        return False


# ── UIDAI stub (swap this for real API later) ─────────────────────────────────

def _send_uidai_otp(aadhaar_hash: str, mobile: str) -> bool:
    """
    TODO: Replace with real UIDAI DigiLocker API call.

    Real implementation would:
    1. POST to https://api.digitallocker.gov.in/public/oauth2/1/token
    2. Use Aadhaar-linked mobile for OTP delivery
    3. Return session token for verification step

    For now: uses worker's registered mobile (same flow, different number).
    """
    return False   # Signal to caller to use registered mobile fallback


# ── Public API ────────────────────────────────────────────────────────────────

def request_kyc_otp(user) -> dict:
    """
    Step 1 — Generate and send KYC OTP to worker's registered mobile.

    Returns
    -------
    dict:
        success  : bool
        message  : str
        mobile   : str (masked)
    """
    mobile = str(user.mobile)

    if not mobile:
        return {"success": False, "message": "No mobile number on account."}

    # Check if KYC already verified
    try:
        if user.kyc.status == "verified":
            return {
                "success": False,
                "message": "KYC is already verified.",
            }
    except Exception:
        pass

    otp = _generate_otp()
    _store_otp(mobile, otp)

    sent = _send_otp_sms(mobile, otp)

    if not sent:
        return {
            "success": False,
            "message": "Failed to send OTP. Please try again.",
        }

    # Mask mobile: show last 4 digits only
    masked = "xxxxxx" + mobile[-4:]

    logger.info("[kyc] OTP sent to %s", masked)

    return {
        "success": True,
        "message": f"OTP sent to {masked}. Valid for 10 minutes.",
        "mobile":  masked,
    }


def verify_kyc_otp(user, otp_entered: str, aadhaar_raw: str = None) -> dict:
    """
    Step 2 — Verify OTP and mark KYC as verified.

    Parameters
    ----------
    user        : authenticated User instance
    otp_entered : OTP string submitted by worker
    aadhaar_raw : 12-digit Aadhaar number (optional, hashed before storage)

    Returns
    -------
    dict:
        success : bool
        message : str
    """
    from apps.accounts.models import KYCRecord

    mobile = str(user.mobile)
    stored = _get_stored_otp(mobile)

    if not stored:
        return {
            "success": False,
            "message": "OTP expired or not requested. Please request a new OTP.",
        }

    if otp_entered.strip() != stored:
        logger.warning("[kyc] Invalid OTP attempt for %s", mobile)
        return {
            "success": False,
            "message": "Invalid OTP. Please try again.",
        }

    # OTP correct — clear it immediately (single use)
    _clear_otp(mobile)

    # Update KYC record
    try:
        kyc, _ = KYCRecord.objects.get_or_create(worker=user)

        if aadhaar_raw:
            cleaned = aadhaar_raw.replace(" ", "").replace("-", "")
            if len(cleaned) == 12 and cleaned.isdigit():
                kyc.set_aadhaar(cleaned)

        kyc.status      = "verified"
        kyc.verified_at = timezone.now()
        kyc.save()

        logger.info("[kyc] KYC verified for user #%s", user.pk)

        return {
            "success": True,
            "message": "KYC verified successfully.",
        }

    except Exception as exc:
        logger.error("[kyc] KYC save error for user #%s: %s", user.pk, exc)
        return {
            "success": False,
            "message": "Verification failed. Please contact support.",
        }


def get_kyc_status(user) -> dict:
    """
    Returns current KYC status for a user.
    """
    try:
        kyc = user.kyc
        return {
            "status":       kyc.status,
            "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
            "verified_at":  kyc.verified_at.isoformat()  if kyc.verified_at  else None,
        }
    except Exception:
        return {
            "status":       "not_started",
            "submitted_at": None,
            "verified_at":  None,
        }