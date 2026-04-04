"""
apps/fraud/tasks.py

daily_batch_fraud_scan  — Layer 6 of the fraud pipeline.
Runs nightly at 2 AM IST via Celery Beat.

Purpose: catch fraud patterns that only become visible in aggregate —
e.g. a worker who has been approved 5 times but whose collective behaviour
(claim velocity, zone patterns, timing) now exceeds the fraud threshold.

What it does
------------
1. Re-scores all approved/on_hold claims from the last 7 days using the
   Isolation Forest (batch mode — faster than real-time).
2. If an already-approved claim now scores ≥ 0.70:
   - Mark claim on_hold for manual review
   - Flag the associated payout if it's still 'credited' (< 24h old)
   - Write a FraudFlag(layer=6) record
   - Send admin notification
3. Returns a summary dict for Celery result tracking.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

RESCAN_REJECT_THRESHOLD = 0.70
RESCAN_WINDOW_DAYS      = 7    # re-check claims from the last N days


@shared_task(name='apps.fraud.tasks.daily_batch_fraud_scan')
def daily_batch_fraud_scan():
    """
    Nightly batch re-scan of recently approved claims.
    Runs at 2 AM IST — scheduled in settings.CELERY_BEAT_SCHEDULE.
    """
    from apps.claims.models import Claim
    from .loader import load_models, models_available, score_claim
    from .models import FraudFlag
    from .service import _write_flag_records

    # Ensure models are loaded for this worker process
    if not models_available():
        load_models()

    cutoff = timezone.now() - timedelta(days=RESCAN_WINDOW_DAYS)

    # Only re-scan approved/on_hold claims — not already-rejected ones
    claims = Claim.objects.filter(
        status__in=['approved', 'on_hold'],
        created_at__gte=cutoff,
    ).select_related(
        'worker', 'worker__workerprofile',
        'disruption_event', 'disruption_event__zone',
        'policy',
    )

    total        = claims.count()
    flagged      = 0
    errors       = 0

    logger.info("[batch_fraud] Starting rescan of %d claims from last %d days.", total, RESCAN_WINDOW_DAYS)

    for claim in claims:
        try:
            iso_score, xgb_score, combined = score_claim(claim)

            if combined >= RESCAN_REJECT_THRESHOLD:
                # This approved claim is now above the reject threshold
                _flag_for_review(claim, combined, iso_score, xgb_score)
                flagged += 1

        except Exception as exc:
            logger.error(
                "[batch_fraud] Error re-scanning claim %s: %s",
                claim.pk, exc, exc_info=True,
            )
            errors += 1

    logger.info(
        "[batch_fraud] Rescan complete — %d scanned, %d flagged, %d errors.",
        total, flagged, errors,
    )
    return {'scanned': total, 'flagged': flagged, 'errors': errors}


def _flag_for_review(claim, combined: float, iso_score: float, xgb_score: float):
    """
    Transition an approved claim to on_hold after batch rescan.
    Also flag the payout if it was credited within the last 24 hours.
    """
    from .models import FraudFlag

    old_status = claim.status

    claim.fraud_score = combined
    claim.status      = 'on_hold'
    detail = (
        f"Nightly batch rescan raised fraud score to {combined:.4f} "
        f"(ISO={iso_score:.4f}, XGB={xgb_score:.4f}). "
        f"Previous status: {old_status}."
    )
    claim.rejection_reason = detail
    claim.save(update_fields=['fraud_score', 'status', 'rejection_reason', 'updated_at'])

    # Write Layer-6 FraudFlag
    FraudFlag.objects.get_or_create(
        claim     = claim,
        layer     = 6,
        flag_type = 'batch_rescan',
        defaults  = {
            'score_contribution': combined,
            'detail':             detail,
        },
    )

    # Flag the associated payout if it is recent
    try:
        payout = claim.payout
        if payout and payout.status == 'credited':
            cutoff_24h = timezone.now() - timedelta(hours=24)
            if payout.credited_at and payout.credited_at >= cutoff_24h:
                payout.status = 'reversed'
                payout.failure_reason = f"Reversed by nightly fraud rescan (score={combined:.4f})"
                payout.save(update_fields=['status', 'failure_reason', 'updated_at'])
                logger.warning(
                    "[batch_fraud] Payout #%s reversed (was credited < 24h ago). Claim #%s",
                    payout.pk, claim.pk,
                )
    except Exception:
        pass

    # Notify admin
    _notify_admin_rescan_flag(claim, combined)

    logger.warning(
        "[batch_fraud] Claim #%s → on_hold after rescan (score=%.4f)",
        claim.pk, combined,
    )


def _notify_admin_rescan_flag(claim, score: float):
    """Queue an admin alert for a batch-rescan flag."""
    try:
        from apps.notifications.tasks import send_admin_alert
        send_admin_alert.delay(
            'fraud_rescan_flag',
            {
                'claim_id':   claim.pk,
                'worker':     claim.worker.mobile,
                'score':      score,
                'zone':       str(claim.disruption_event.zone) if claim.disruption_event else '—',
                'amount':     str(claim.payout_amount),
            },
        )
    except Exception as e:
        logger.warning("[batch_fraud] Could not queue admin notification: %s", e)
