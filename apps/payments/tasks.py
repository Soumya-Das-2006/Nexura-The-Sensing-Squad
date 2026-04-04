"""
apps/payments/tasks.py

collect_weekly_premiums
    Runs every Monday at 12:01 AM IST via Celery Beat.
    For every active policy, either:
      - Razorpay Autopay handles the debit automatically (if mandate is confirmed)
      - We create a PremiumPayment record and mark it captured (sandbox)
      - If debit fails → use grace token (if available) or pause policy

handle_payment_failure(policy_id)
    Called when a Razorpay webhook reports a subscription payment failure.
    Sends a WhatsApp warning, then pauses the policy after 2 consecutive failures.
"""
import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _this_monday() -> date:
    """Return the date of the most recent Monday (or today if Monday)."""
    today = timezone.now().date()
    return today - timedelta(days=today.weekday())


# ─── Main weekly task ─────────────────────────────────────────────────────────

@shared_task(name='apps.payments.tasks.collect_weekly_premiums')
def collect_weekly_premiums():
    """
    Monday 12:01 AM — collect premiums for all active policies.

    For real Razorpay Autopay mandates, Razorpay handles the debit automatically
    and sends a webhook. This task creates the PremiumPayment record optimistically
    (status=pending) so we have an audit trail even before the webhook arrives.

    In sandbox mode (no real Razorpay credentials), it immediately marks captured.
    """
    from apps.policies.models import Policy
    from .models import PremiumPayment

    week_start  = _this_monday()
    active_policies = Policy.objects.filter(
        status='active',
        mandate_confirmed=True,
    ).select_related('worker', 'worker__workerprofile', 'plan_tier')

    collected = 0
    skipped   = 0

    for policy in active_policies:
        # Idempotency — skip if already have a record for this week
        if PremiumPayment.objects.filter(policy=policy, week_start_date=week_start).exists():
            skipped += 1
            continue

        payment = PremiumPayment.objects.create(
            policy          = policy,
            worker          = policy.worker,
            amount          = policy.weekly_premium,
            week_start_date = week_start,
            razorpay_subscription_id = policy.razorpay_subscription_id,
            status          = 'pending',
        )

        # In sandbox mode, immediately capture
        from apps.payouts.razorpay_service import _is_sandbox
        if _is_sandbox():
            import uuid
            payment.capture(
                razorpay_payment_id=f"pay_{uuid.uuid4().hex[:16]}",
                signature='sandbox',
            )
            # Extend the policy by one more week
            policy.end_date = policy.end_date + timedelta(days=7)
            policy.save(update_fields=['end_date'])
            collected += 1
            logger.info(
                "[collect_weekly] SANDBOX: Captured ₹%s from %s for week %s",
                payment.amount, policy.worker.mobile, week_start,
            )
        else:
            # Real mode — Razorpay fires the debit; we wait for the webhook
            collected += 1
            logger.info(
                "[collect_weekly] PremiumPayment #%s created (pending Razorpay debit) — %s",
                payment.pk, policy.worker.mobile,
            )

    logger.info(
        "[collect_weekly] Week %s — %d payments queued, %d skipped.",
        week_start, collected, skipped,
    )
    return {'week': str(week_start), 'collected': collected, 'skipped': skipped}


# ─── Handle payment failure ───────────────────────────────────────────────────

@shared_task(name='apps.payments.tasks.handle_payment_failure')
def handle_payment_failure(policy_id: int, payment_id: int, reason: str = ''):
    """
    Called when a Razorpay subscription webhook reports a payment.failed event.
    Logic:
      1. If worker has grace tokens remaining → use one, keep policy active.
      2. If no grace tokens → send warning WhatsApp + pause the policy.
    """
    from apps.policies.models import Policy
    from .models import PremiumPayment

    try:
        policy  = Policy.objects.select_related(
            'worker', 'worker__workerprofile'
        ).get(pk=policy_id)
        payment = PremiumPayment.objects.get(pk=payment_id)
    except (Policy.DoesNotExist, PremiumPayment.DoesNotExist) as e:
        logger.error("[handle_payment_failure] %s", e)
        return

    profile = getattr(policy.worker, 'workerprofile', None)
    payment.fail(reason=reason)

    if profile and profile.grace_tokens > 0:
        # Use grace token
        profile.grace_tokens -= 1
        profile.save(update_fields=['grace_tokens'])
        payment.use_grace()

        logger.info(
            "[payment_failure] Grace token used for %s. Tokens remaining: %d",
            policy.worker.mobile, profile.grace_tokens,
        )
        _notify_grace_used(policy)

    else:
        # No grace tokens — pause the policy
        policy.status = 'paused'
        policy.save(update_fields=['status'])

        logger.warning(
            "[payment_failure] Policy %s PAUSED — no grace tokens. Worker: %s",
            policy.pk, policy.worker.mobile,
        )
        _notify_payment_failed(policy, reason)


# ─── Notification helpers ─────────────────────────────────────────────────────

def _notify_grace_used(policy):
    try:
        from apps.notifications.tasks import send_payment_notification
        send_payment_notification.delay(policy.worker.pk, 'grace_used')
    except Exception as e:
        logger.warning("[payments] Could not queue grace notification: %s", e)


def _notify_payment_failed(policy, reason: str):
    try:
        from apps.notifications.tasks import send_payment_notification
        send_payment_notification.delay(policy.worker.pk, 'payment_failed', {'reason': reason})
    except Exception as e:
        logger.warning("[payments] Could not queue failure notification: %s", e)


def _notify_payment_captured(policy, amount):
    try:
        from apps.notifications.tasks import send_payment_notification
        send_payment_notification.delay(policy.worker.pk, 'payment_captured', {'amount': str(amount)})
    except Exception as e:
        logger.warning("[payments] Could not queue capture notification: %s", e)
