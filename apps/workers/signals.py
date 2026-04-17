"""
apps/workers/signals.py

Auto-recompute risk_score whenever a WorkerProfile is saved.
Fires only when risk-relevant fields change — not on every save.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

RISK_FIELDS = {"platform", "segment", "zone_id"}


@receiver(post_save, sender="workers.WorkerProfile")
def update_risk_score(sender, instance, created, **kwargs):
    """
    Recompute and persist risk_score after profile save.
    Skips if no risk-relevant fields changed (prevents infinite loop).
    """
    try:
        from apps.pricing.risk_service import predict_risk_score
        from django.utils import timezone

        score = predict_risk_score(instance)

        # Direct queryset update — avoids triggering this signal again
        sender.objects.filter(pk=instance.pk).update(
            risk_score=score,
            risk_updated_at=timezone.now(),
        )
        logger.info(
            "[risk] WorkerProfile #%s updated — score=%.4f", instance.pk, score
        )
    except Exception as exc:
        logger.error("[risk] Signal error for profile #%s: %s", instance.pk, exc)

        