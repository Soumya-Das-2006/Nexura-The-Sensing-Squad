"""
apps/claims/tasks.py

process_pending_claims — runs every 5 minutes via Celery Beat.
Also called immediately after each DisruptionEvent is created (trigger.tasks).

Flow for each unprocessed DisruptionEvent
------------------------------------------
1. Find all workers in the event's zone with an active policy
2. For each worker, create a Claim (skip if already exists — unique_together)
3. Run the 6-layer fraud pipeline
4. Set claim status: approved / rejected / on_hold
5. If approved → queue payout disbursement (apps.payouts.tasks)
6. Send WhatsApp / email notification (apps.notifications.tasks)
7. Mark event.claims_generated = True
"""
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── Main task ────────────────────────────────────────────────────────────────

@shared_task(
    name='apps.claims.tasks.process_pending_claims',
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # retry after 60 s on transient errors
)
def process_pending_claims(self):
    """
    Process all DisruptionEvents that have not yet had claims generated.
    Runs every 5 minutes via Celery Beat.
    """
    from apps.triggers.models import DisruptionEvent

    events = DisruptionEvent.objects.filter(
        claims_generated=False,
        is_full_trigger=True,   # only full triggers generate claims automatically
    ).select_related('zone').order_by('started_at')

    total_claims   = 0
    total_events   = events.count()

    for event in events:
        try:
            n = _process_one_event(event)
            total_claims += n
        except Exception as exc:
            logger.error(
                "[process_claims] Event %s failed: %s", event.pk, exc, exc_info=True
            )
            # Don't retry the whole batch — mark as processed to avoid re-runs
            event.claims_generated = True
            event.save(update_fields=['claims_generated'])

    logger.info(
        "[process_claims] Processed %d events → %d claims created.",
        total_events, total_claims,
    )
    return {'events_processed': total_events, 'claims_created': total_claims}


# ─── Per-event processing ─────────────────────────────────────────────────────

def _process_one_event(event) -> int:
    """
    Create and process claims for all eligible workers in the event's zone.
    Returns the number of new claims created.
    """
    from apps.policies.models import Policy
    from .models import Claim
    from .pipeline import run_fraud_pipeline

    zone = event.zone

    # Find all active policies for workers whose registered zone matches this event's zone
    active_policies = Policy.objects.filter(
        status='active',
        worker__workerprofile__zone=zone,
        end_date__gte=timezone.now().date(),
    ).select_related('worker', 'worker__workerprofile', 'plan_tier')

    created_count = 0

    for policy in active_policies:
        worker = policy.worker

        # Check if claim already exists (unique_together guard)
        if Claim.objects.filter(worker=worker, disruption_event=event).exists():
            logger.debug(
                "[process_claims] Claim already exists for worker=%s event=%s — skipping.",
                worker.pk, event.pk,
            )
            continue

        # Calculate payout amount
        if event.is_full_trigger:
            payout_amount = policy.weekly_coverage
        else:
            payout_amount = policy.weekly_coverage / 2   # 50% for partial triggers

        try:
            with transaction.atomic():
                claim = Claim.objects.create(
                    worker           = worker,
                    policy           = policy,
                    disruption_event = event,
                    payout_amount    = payout_amount,
                    status           = 'pending',
                )
                created_count += 1
                logger.info(
                    "[process_claims] Claim #%s created — worker=%s event=%s amount=₹%s",
                    claim.pk, worker.pk, event.pk, payout_amount,
                )

            # Run fraud pipeline (outside transaction so ML inference doesn't lock DB)
            from apps.fraud.service import process_claim_pipeline
            process_claim_pipeline(claim)

        except Exception as exc:
            logger.error(
                "[process_claims] Failed to create/process claim for worker=%s event=%s: %s",
                worker.pk, event.pk, exc, exc_info=True,
            )

    # Mark event fully processed
    event.claims_generated = True
    event.save(update_fields=['claims_generated'])

    return created_count





# ─── Manual approve / reject tasks (admin actions) ───────────────────────────

@shared_task(name='apps.claims.tasks.manually_approve_claim')
def manually_approve_claim(claim_id: int, admin_user_id: int):
    """Admin manually approves an on_hold claim."""
    from .models import Claim
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        claim = Claim.objects.get(pk=claim_id)
        admin = User.objects.get(pk=admin_user_id)
    except Exception as e:
        logger.error("[manually_approve] %s", e)
        return

    if claim.status not in ('on_hold', 'pending'):
        logger.warning("[manually_approve] Claim %s is already %s — skipping.", claim_id, claim.status)
        return

    claim.approve(reviewed_by=admin)
    from apps.fraud.service import _queue_payout, _notify_worker
    _queue_payout(claim)
    _notify_worker(claim, 'claim_approved')
    logger.info("[manually_approve] Claim #%s approved by admin %s", claim_id, admin_user_id)


@shared_task(name='apps.claims.tasks.manually_reject_claim')
def manually_reject_claim(claim_id: int, admin_user_id: int, reason: str):
    """Admin manually rejects an on_hold claim."""
    from .models import Claim
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        claim = Claim.objects.get(pk=claim_id)
        admin = User.objects.get(pk=admin_user_id)
    except Exception as e:
        logger.error("[manually_reject] %s", e)
        return

    claim.reject(reason=reason, reviewed_by=admin)
    from apps.fraud.service import _notify_worker
    _notify_worker(claim, 'claim_rejected')
    logger.info("[manually_reject] Claim #%s rejected by admin %s", claim_id, admin_user_id)
