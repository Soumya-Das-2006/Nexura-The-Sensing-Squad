"""
apps/payouts/tasks.py

disburse_payout(claim_id)
    Called immediately after a claim is approved (from claims.tasks._queue_payout).
    Creates the Payout record and calls Razorpay.

reconcile_payouts()
    Runs every 10 minutes. Polls Razorpay for status of pending/queued payouts
    and updates the local record when they are credited or failed.

retry_failed_payouts()
    Runs every hour. Re-attempts failed payouts up to MAX_RETRIES times.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_RETRIES       = 3
RETRY_DELAY_SECS  = 300   # 5 minutes between retries


# ─── Primary task: disburse a single payout ──────────────────────────────────

@shared_task(
    name='apps.payouts.tasks.disburse_payout',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def disburse_payout(self, claim_id: int):
    """
    Create a Payout record and initiate transfer via Razorpay Payouts API.
    Called automatically when a claim is approved.
    """
    from apps.claims.models import Claim
    from .models import Payout
    from .razorpay_service import create_payout

    try:
        claim = Claim.objects.select_related(
            'worker', 'worker__workerprofile',
            'disruption_event', 'disruption_event__zone',
        ).get(pk=claim_id)
    except Claim.DoesNotExist:
        logger.error("[disburse_payout] Claim %s not found.", claim_id)
        return

    if claim.status != 'approved':
        logger.warning(
            "[disburse_payout] Claim %s is not approved (status=%s) — skipping.",
            claim_id, claim.status,
        )
        return

    # Idempotency: don't create a second payout if one already exists
    if Payout.objects.filter(claim=claim).exists():
        logger.info("[disburse_payout] Payout already exists for claim %s.", claim_id)
        return

    # Create the Payout record in PENDING state first
    payout = Payout.objects.create(
        claim   = claim,
        worker  = claim.worker,
        amount  = claim.payout_amount,
        mode    = 'UPI',
        status  = 'pending',
    )
    logger.info(
        "[disburse_payout] Payout #%s created for claim %s — ₹%s → %s",
        payout.pk, claim_id, payout.amount, claim.worker.mobile,
    )

    # Call Razorpay
    try:
        result = create_payout(payout)

        rp_id  = result.get('razorpay_payout_id', '')
        status = result.get('status', 'queued')
        utr    = result.get('utr', '')

        payout.razorpay_payout_id    = rp_id
        payout.razorpay_fund_acct_id = getattr(
            claim.worker.workerprofile, 'razorpay_fund_acct_id', ''
        )

        if status in ('processed', 'credited') or result.get('sandbox'):
            payout.mark_credited(utr=utr or _generate_sandbox_utr(), razorpay_id=rp_id)
            logger.info(
                "[disburse_payout] Payout #%s CREDITED — UTR=%s",
                payout.pk, payout.utr_number,
            )
            # Send success notification
            _notify_payout_credited(payout)

        else:
            payout.status = 'queued'
            payout.save(update_fields=['razorpay_payout_id', 'razorpay_fund_acct_id', 'status', 'updated_at'])
            logger.info(
                "[disburse_payout] Payout #%s QUEUED at Razorpay (rp_id=%s).",
                payout.pk, rp_id,
            )

    except Exception as exc:
        logger.error(
            "[disburse_payout] Payout #%s failed: %s",
            payout.pk, exc, exc_info=True,
        )
        payout.mark_failed(reason=str(exc))

        # Retry the task
        try:
            raise self.retry(exc=exc, countdown=RETRY_DELAY_SECS)
        except self.MaxRetriesExceededError:
            logger.error(
                "[disburse_payout] Max retries exceeded for payout #%s.", payout.pk
            )
            _notify_payout_failed(payout)


# ─── Reconciliation task ─────────────────────────────────────────────────────

@shared_task(name='apps.payouts.tasks.reconcile_payouts')
def reconcile_payouts():
    """
    Poll Razorpay for the status of payouts that are still pending/queued.
    Runs every 10 minutes.
    """
    from .models import Payout
    from .razorpay_service import get_payout_status

    stale = Payout.objects.filter(
        status__in=['queued', 'processing'],
        razorpay_payout_id__gt='',   # has a real Razorpay ID
    ).exclude(
        razorpay_payout_id__startswith='pout_',   # exclude sandbox fakes
    )

    updated = 0
    for payout in stale:
        try:
            result = get_payout_status(payout.razorpay_payout_id)
            status = result.get('status')

            if status == 'processed':
                payout.mark_credited(
                    utr=result.get('utr', ''),
                    razorpay_id=payout.razorpay_payout_id,
                )
                _notify_payout_credited(payout)
                updated += 1

            elif status == 'failed':
                payout.mark_failed(result.get('failure_reason', 'Razorpay reported failure'))
                _notify_payout_failed(payout)
                updated += 1

            elif status == 'reversed':
                payout.status = 'reversed'
                payout.save(update_fields=['status', 'updated_at'])
                updated += 1

        except Exception as exc:
            logger.error("[reconcile_payouts] Error for payout %s: %s", payout.pk, exc)

    logger.info("[reconcile_payouts] Reconciled %d payouts.", updated)
    return {'updated': updated}


# ─── Retry failed payouts ─────────────────────────────────────────────────────

@shared_task(name='apps.payouts.tasks.retry_failed_payouts')
def retry_failed_payouts():
    """
    Re-attempt failed payouts up to MAX_RETRIES times.
    Runs every hour.
    """
    from .models import Payout

    failed = Payout.objects.filter(
        status='failed',
        retry_count__lt=MAX_RETRIES,
    )

    for payout in failed:
        payout.retry_count    += 1
        payout.last_retry_at   = timezone.now()
        payout.status          = 'pending'
        payout.save(update_fields=['retry_count', 'last_retry_at', 'status', 'updated_at'])

        disburse_payout.delay(payout.claim_id)
        logger.info(
            "[retry_failed_payouts] Re-queued payout #%s (attempt %d/%d)",
            payout.pk, payout.retry_count, MAX_RETRIES,
        )

    return {'retried': failed.count()}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_sandbox_utr() -> str:
    import uuid
    return f"NEXURA{uuid.uuid4().hex[:10].upper()}"


def _notify_payout_credited(payout):
    """Queue a 'payout credited' WhatsApp notification."""
    try:
        from apps.notifications.tasks import send_payout_notification
        send_payout_notification.delay(payout.pk, 'credited')
    except Exception as e:
        logger.warning("[disburse_payout] Could not queue notification: %s", e)


def _notify_payout_failed(payout):
    """Queue a 'payout failed' WhatsApp notification."""
    try:
        from apps.notifications.tasks import send_payout_notification
        send_payout_notification.delay(payout.pk, 'failed')
    except Exception as e:
        logger.warning("[disburse_payout] Could not queue failure notification: %s", e)
