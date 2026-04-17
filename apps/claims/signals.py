"""
apps/claims/signals.py

Auto-score fraud whenever a Claim is created.
Only fires on creation (not every update) to avoid re-scoring approved claims.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="claims.Claim")
def score_claim_on_create(sender, instance, created, **kwargs):
    """
    Score fraud immediately after a new claim is created.
    Skips if claim already has a fraud_score (manually set or re-saved).
    """
    if not created:
        return

    if instance.fraud_score and instance.fraud_score > 0:
        return

    try:
        from apps.fraud.fraud_service import score_claim, is_available, _load

        if not is_available():
            _load()

        score = score_claim(instance)

        # Direct queryset update — avoids re-triggering this signal
        sender.objects.filter(pk=instance.pk).update(fraud_score=score)

        logger.info(
            "[fraud] Claim #%s scored — fraud_score=%.4f", instance.pk, score
        )

        # Auto-flag high-risk claims for admin review
        if score >= 0.75:
            sender.objects.filter(pk=instance.pk).update(status="flagged")
            logger.warning(
                "[fraud] Claim #%s AUTO-FLAGGED — score=%.4f", instance.pk, score
            )

    except Exception as exc:
        logger.error(
            "[fraud] Signal error for claim #%s: %s", instance.pk, exc
        )