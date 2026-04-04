"""
apps/payouts/razorpay_service.py

Razorpay Payouts API integration.

All interactions with Razorpay live in this single module so that:
  - The Celery task stays clean (just calls these functions)
  - Mocking in tests is straightforward
  - Sandbox mode is handled transparently

Razorpay Payouts flow
----------------------
1. ensure_contact(worker_profile)  → razorpay_contact_id  on WorkerProfile
2. ensure_fund_account(profile)    → razorpay_fund_acct_id on WorkerProfile
3. create_payout(payout_obj)       → razorpay_payout_id on Payout
4. get_payout_status(razorpay_id)  → poll for status changes
"""
import logging
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── Sandbox helpers ──────────────────────────────────────────────────────────

def _is_sandbox() -> bool:
    """True when Razorpay credentials are not configured (dev / test mode)."""
    key = settings.RAZORPAY_KEY_ID
    return not key or key.startswith('rzp_test_xxx') or not settings.RAZORPAY_KEY_SECRET


def _get_client():
    """Return an authenticated Razorpay client."""
    import razorpay
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ─── Step 1: Ensure Contact ───────────────────────────────────────────────────

def ensure_contact(profile) -> str:
    """
    Create a Razorpay Contact for the worker if one doesn't exist yet.
    Stores the contact_id on WorkerProfile and returns it.
    """
    if profile.razorpay_contact_id:
        return profile.razorpay_contact_id

    if _is_sandbox():
        fake_id = f"cont_{uuid.uuid4().hex[:14]}"
        logger.info("[Razorpay SANDBOX] Fake contact created: %s", fake_id)
        profile.razorpay_contact_id = fake_id
        profile.save(update_fields=['razorpay_contact_id'])
        return fake_id

    try:
        client  = _get_client()
        contact = client.contact.create({
            'name':         profile.name,
            'contact':      f'+91{profile.user.mobile}',
            'type':         'employee',           # closest type for gig workers
            'reference_id': str(profile.user.pk),
            'notes': {
                'platform': profile.platform,
                'city':     profile.city,
            },
        })
        contact_id = contact['id']
        profile.razorpay_contact_id = contact_id
        profile.save(update_fields=['razorpay_contact_id'])
        logger.info("[Razorpay] Contact created: %s for worker %s", contact_id, profile.user.mobile)
        return contact_id

    except Exception as exc:
        logger.error("[Razorpay] Contact creation failed for %s: %s", profile.user.mobile, exc)
        raise


# ─── Step 2: Ensure Fund Account ──────────────────────────────────────────────

def ensure_fund_account(profile) -> str:
    """
    Create a Razorpay Fund Account (UPI) for the worker if one doesn't exist.
    Stores the fund_acct_id on WorkerProfile and returns it.
    """
    if profile.razorpay_fund_acct_id:
        return profile.razorpay_fund_acct_id

    if not profile.upi_id:
        raise ValueError(f"Worker {profile.user.mobile} has no UPI ID set.")

    if _is_sandbox():
        fake_id = f"fa_{uuid.uuid4().hex[:16]}"
        logger.info("[Razorpay SANDBOX] Fake fund account created: %s", fake_id)
        profile.razorpay_fund_acct_id = fake_id
        profile.save(update_fields=['razorpay_fund_acct_id'])
        return fake_id

    contact_id = ensure_contact(profile)

    try:
        client      = _get_client()
        fund_acct   = client.fund_account.create({
            'contact_id':    contact_id,
            'account_type':  'vpa',
            'vpa': {
                'address': profile.upi_id,
            },
        })
        fa_id = fund_acct['id']
        profile.razorpay_fund_acct_id = fa_id
        profile.save(update_fields=['razorpay_fund_acct_id'])
        logger.info("[Razorpay] Fund account created: %s for UPI %s", fa_id, profile.upi_id)
        return fa_id

    except Exception as exc:
        logger.error(
            "[Razorpay] Fund account creation failed for %s: %s",
            profile.user.mobile, exc
        )
        raise


# ─── Step 3: Create Payout ────────────────────────────────────────────────────

def create_payout(payout_obj) -> dict:
    """
    Initiate a Razorpay payout for the given Payout model instance.

    Sandbox mode:
      - Generates a fake UTR and immediately marks the payout as credited.
      - Simulates the real flow without hitting Razorpay.

    Returns a dict:
      {'razorpay_payout_id': str, 'status': str, 'utr': str | None}
    """
    worker  = payout_obj.worker
    amount  = payout_obj.amount
    claim   = payout_obj.claim

    try:
        profile = worker.workerprofile
    except Exception:
        raise ValueError(f"Worker {worker.mobile} has no WorkerProfile.")

    # ── Sandbox mode ──────────────────────────────────────────────────────
    if _is_sandbox():
        fake_rp_id = f"pout_{uuid.uuid4().hex[:16]}"
        fake_utr   = f"UTR{uuid.uuid4().hex[:12].upper()}"
        logger.info(
            "[Razorpay SANDBOX] Payout simulated: id=%s utr=%s amount=₹%s worker=%s",
            fake_rp_id, fake_utr, amount, worker.mobile,
        )
        return {
            'razorpay_payout_id': fake_rp_id,
            'status':             'processed',
            'utr':                fake_utr,
            'sandbox':            True,
        }

    # ── Real Razorpay call ────────────────────────────────────────────────
    fa_id = ensure_fund_account(profile)

    client = _get_client()
    try:
        payout_data = client.payout.create({
            'account_number': settings.RAZORPAY_ACCOUNT_NUMBER,
            'fund_account_id': fa_id,
            'amount':          int(amount * 100),   # Razorpay uses paise
            'currency':        'INR',
            'mode':            'UPI',
            'purpose':         'payout',
            'queue_if_low_balance': True,
            'reference_id':    f"NEXURA-CLAIM-{claim.pk}",
            'narration':       f"Nexura claim payout #{claim.pk}",
            'notes': {
                'claim_id':     str(claim.pk),
                'trigger_type': claim.disruption_event.trigger_type if claim.disruption_event else '',
                'zone':         str(claim.disruption_event.zone) if claim.disruption_event else '',
            },
        })

        rp_id  = payout_data.get('id', '')
        status = payout_data.get('status', 'queued')
        utr    = payout_data.get('utr', '')

        logger.info(
            "[Razorpay] Payout created: id=%s status=%s amount=₹%s worker=%s",
            rp_id, status, amount, worker.mobile,
        )
        return {'razorpay_payout_id': rp_id, 'status': status, 'utr': utr}

    except Exception as exc:
        logger.error(
            "[Razorpay] Payout creation failed for claim %s worker %s: %s",
            claim.pk, worker.mobile, exc,
        )
        raise


# ─── Step 4: Poll payout status ───────────────────────────────────────────────

def get_payout_status(razorpay_payout_id: str) -> dict:
    """
    Fetch the current status of a Razorpay payout.

    Returns:
      {'status': str, 'utr': str | None, 'failure_reason': str | None}
    """
    if _is_sandbox() or razorpay_payout_id.startswith('pout_'):
        return {'status': 'processed', 'utr': f"UTR{uuid.uuid4().hex[:12].upper()}", 'failure_reason': None}

    try:
        client = _get_client()
        data   = client.payout.fetch(razorpay_payout_id)
        return {
            'status':         data.get('status', 'queued'),
            'utr':            data.get('utr', ''),
            'failure_reason': data.get('error', {}).get('description', '') if data.get('status') == 'failed' else None,
        }
    except Exception as exc:
        logger.error("[Razorpay] Status fetch failed for %s: %s", razorpay_payout_id, exc)
        return {'status': 'unknown', 'utr': None, 'failure_reason': str(exc)}


# ─── Webhook payload validator ────────────────────────────────────────────────

def verify_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verify the X-Razorpay-Signature header on incoming webhooks.
    Returns True if valid.
    """
    import hmac
    import hashlib

    secret  = settings.RAZORPAY_WEBHOOK_SECRET.encode()
    digest  = hmac.new(secret, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
