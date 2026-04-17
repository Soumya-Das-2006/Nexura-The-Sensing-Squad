"""
apps/fraud/service.py

The authoritative 6-layer fraud detection pipeline.
This replaces the simplified version in apps/claims/pipeline.py.
apps/claims/pipeline.py now delegates to this module.

Layer 1 — Parametric Gate          no event? → reject
Layer 2 — Duplicate Prevention     already exists? → reject
Layer 3 — GPS Zone Validation       wrong zone? → flag (+0.30)
Layer 4 — ML Score                  IsolationForest + XGBoost (real trained models)
Layer 5 — Score Routing             <0.50 approve / 0.50–0.70 hold / >0.70 reject
Layer 6 — Nightly Batch Rescan     daily_batch_fraud_scan task (this file, tasks.py)

Returns
-------
{
    'decision':         'approve' | 'hold' | 'reject',
    'fraud_score':      float,
    'iso_score':        float,
    'xgb_score':        float,
    'flags':            list[dict],
    'rejection_reason': str,
}
"""
import logging
from django.utils import timezone

from .loader import load_models, models_available, score_claim, build_feature_vector
from .models import FraudFlag

logger = logging.getLogger(__name__)

# Load models on import (non-blocking — falls back to heuristic if unavailable)
load_models()

# Score thresholds
APPROVE_THRESHOLD = 0.50
REJECT_THRESHOLD  = 0.70


def run_fraud_pipeline(claim) -> dict:
    """
    Run the complete 6-layer fraud pipeline on a Claim.
    Writes FraudFlag records for each layer that produces a signal.

    Returns a result dict. The caller updates claim.fraud_score, claim.fraud_flags,
    and claim.status based on result['decision'].
    """
    flags  = []
    result = {
        'decision':         'approve',
        'fraud_score':      0.0,
        'iso_score':        0.0,
        'xgb_score':        0.0,
        'flags':            flags,
        'rejection_reason': '',
    }

    worker = claim.worker
    event  = claim.disruption_event
    policy = claim.policy

    # ── LAYER 1: Parametric Gate ──────────────────────────────────────────
    layer1_result = _layer1_parametric_gate(claim, event, flags)
    if layer1_result == 'reject':
        result['decision']         = 'reject'
        result['rejection_reason'] = 'No qualifying disruption event found for your zone.'
        result['flags']            = flags
        _write_flag_records(claim, flags)
        return result

    # ── LAYER 2: Duplicate Prevention ────────────────────────────────────
    if _layer2_duplicate(claim, event, flags) == 'reject':
        result['decision']         = 'reject'
        result['rejection_reason'] = 'Duplicate claim — a claim for this event already exists.'
        result['flags']            = flags
        _write_flag_records(claim, flags)
        return result

    # ── LAYER 3: GPS Zone Validation ─────────────────────────────────────
    _layer3_gps_zone(claim, event, worker, flags)

    # ── LAYER 4: ML Score ─────────────────────────────────────────────────
    iso_score, xgb_score, combined = _layer4_ml_score(claim, event, flags)
    result['iso_score']  = iso_score
    result['xgb_score']  = xgb_score
    result['fraud_score'] = combined

    # ── LAYER 5: Score Routing ────────────────────────────────────────────
    decision = _layer5_routing(claim, combined, flags)
    result['decision'] = decision

    if decision == 'reject':
        result['rejection_reason'] = (
            f"Automated fraud detection flagged this claim "
            f"(score: {combined:.2f}). Contact support if you believe this is an error."
        )

    result['flags'] = flags
    _write_flag_records(claim, flags)
    return result


# ── Layer implementations ─────────────────────────────────────────────────────

def _layer1_parametric_gate(claim, event, flags: list) -> str:
    """Returns 'pass' or 'reject'."""
    if event is None:
        flags.append({
            'layer': 1, 'flag': 'no_event',
            'detail': 'No DisruptionEvent linked to this claim.',
            'score_contribution': 1.0,
        })
        return 'reject'

    if not event.is_full_trigger:
        flags.append({
            'layer': 1, 'flag': 'partial_trigger',
            'detail': (
                f"Trigger severity {event.severity_value:.1f} is below full threshold "
                f"{event.threshold_value:.0f} — 50% payout applied."
            ),
            'score_contribution': 0.0,
        })
        # Partial trigger still passes — payout is halved upstream

    return 'pass'


def _layer2_duplicate(claim, event, flags: list) -> str:
    """Returns 'pass' or 'reject'."""
    from apps.claims.models import Claim
    dup = Claim.objects.filter(
        worker=claim.worker,
        disruption_event=event,
    ).exclude(pk=claim.pk).exists()

    if dup:
        flags.append({
            'layer': 2, 'flag': 'duplicate',
            'detail': 'A claim for this disruption event already exists for this worker.',
            'score_contribution': 1.0,
        })
        return 'reject'
    return 'pass'


def _layer3_gps_zone(claim, event, worker, flags: list):
    """Adds flags for zone mismatch. No reject at this layer."""
    try:
        profile     = worker.workerprofile
        worker_zone = profile.zone
        event_zone  = event.zone if event else None

        if worker_zone is None or event_zone is None:
            flags.append({
                'layer': 3, 'flag': 'gps_missing',
                'detail': 'Zone data unavailable — GPS check skipped.',
                'score_contribution': 0.05,
            })
            return

        if worker_zone.pk != event_zone.pk:
            from .loader import _haversine
            dist = _haversine(
                float(worker_zone.lat), float(worker_zone.lng),
                float(event_zone.lat),  float(event_zone.lng),
            )
            contribution = 0.15 if dist < 5.0 else 0.30 if dist < 15.0 else 0.50
            flags.append({
                'layer': 3, 'flag': 'zone_mismatch',
                'detail': (
                    f"Worker registered in {worker_zone.area_name} ({worker_zone.city}) "
                    f"but event is in {event_zone.area_name} ({event_zone.city}). "
                    f"Distance ≈ {dist:.1f} km."
                ),
                'score_contribution': contribution,
            })

    except Exception as exc:
        logger.debug("[Layer 3] GPS check error: %s", exc)
        flags.append({
            'layer': 3, 'flag': 'gps_missing',
            'detail': f"GPS check skipped: {exc}",
            'score_contribution': 0.0,
        })


def _layer4_ml_score(claim, event, flags: list) -> tuple[float, float, float]:
    """Run ML models. Returns (iso_score, xgb_score, combined)."""
    if not models_available():
        load_models()

    if models_available():
        iso_score, xgb_score, combined = score_claim(claim)
        flags.append({
            'layer': 4, 'flag': 'iso_anomaly' if iso_score > 0.5 else 'score_approve',
            'detail': (
                f"IsolationForest score: {iso_score:.4f} | "
                f"XGBoost P(fraud): {xgb_score:.4f} | "
                f"Ensemble (60% XGB + 40% ISO): {combined:.4f}"
            ),
            'score_contribution': combined,
        })
    else:
        # Heuristic fallback
        iso_score = xgb_score = 0.0
        combined  = _heuristic_score(claim, flags)

    return iso_score, xgb_score, combined


def _layer5_routing(claim, score: float, flags: list) -> str:
    """Route based on score. Returns 'approve', 'hold', or 'reject'."""
    if score >= REJECT_THRESHOLD:
        flags.append({
            'layer': 5, 'flag': 'score_reject',
            'detail': f"Score {score:.4f} ≥ {REJECT_THRESHOLD} — auto-rejected.",
            'score_contribution': score,
        })
        return 'reject'
    elif score >= APPROVE_THRESHOLD:
        flags.append({
            'layer': 5, 'flag': 'score_hold',
            'detail': f"Score {score:.4f} in review band ({APPROVE_THRESHOLD}–{REJECT_THRESHOLD}) — held for manual review.",
            'score_contribution': score,
        })
        return 'hold'
    else:
        flags.append({
            'layer': 5, 'flag': 'score_approve',
            'detail': f"Score {score:.4f} < {APPROVE_THRESHOLD} — auto-approved.",
            'score_contribution': score,
        })
        return 'approve'


# ── Fraud Pipeline Wrapper & Router ──────────────────────────────────────────

def process_claim_pipeline(claim):
    """
    Validates claim, runs fraud pipeline, updates claim status,
    and queues payouts/notifications.
    """
    logger.info("[process_claim_pipeline] Starting pipeline for Claim #%s", claim.pk)

    # 1. Validation
    if not claim.policy or claim.payout_amount <= 0:
        logger.error("[process_claim_pipeline] Claim #%s failed pre-validation", claim.pk)
        claim.status = 'rejected'
        claim.rejection_reason = 'Invalid claim parameters.'
        claim.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        _notify_worker(claim, 'claim_rejected')
        return

    # 2. Run Pipeline
    try:
        result = run_fraud_pipeline(claim)
    except Exception as e:
        logger.error("[process_claim_pipeline] Pipeline crashed for Claim #%s: %s", claim.pk, e, exc_info=True)
        # Fail safe
        claim.status = 'on_hold'
        claim.save(update_fields=['status', 'updated_at'])
        _notify_worker(claim, 'claim_under_review')
        return

    claim.fraud_score = result['fraud_score']
    claim.fraud_flags = result['flags']
    decision = result['decision']

    # 3. Route based on decision
    if decision == 'approve':
        claim.status = 'approved'
        claim.save(update_fields=['status', 'fraud_score', 'fraud_flags', 'updated_at'])
        logger.info("[pipeline] Claim #%s → APPROVED (score=%.3f)", claim.pk, claim.fraud_score)
        _queue_payout(claim)
        _notify_worker(claim, 'claim_approved')

    elif decision == 'hold':
        claim.status = 'on_hold'
        claim.save(update_fields=['status', 'fraud_score', 'fraud_flags', 'updated_at'])
        logger.info("[pipeline] Claim #%s → ON HOLD (score=%.3f)", claim.pk, claim.fraud_score)
        _notify_worker(claim, 'claim_under_review')

    elif decision == 'reject':
        claim.status           = 'rejected'
        claim.rejection_reason = result.get('rejection_reason', 'Fraud detection flagged this claim.')
        claim.save(update_fields=[
            'status', 'fraud_score', 'fraud_flags', 'rejection_reason', 'updated_at'
        ])
        logger.info("[pipeline] Claim #%s → REJECTED (score=%.3f)", claim.pk, claim.fraud_score)
        _notify_worker(claim, 'claim_rejected')


def _queue_payout(claim):
    """Queue the payout disbursement task."""
    try:
        from apps.payouts.tasks import disburse_payout
        disburse_payout.delay(claim.pk)
    except Exception as e:
        logger.error("[process_claims] Could not queue payout for claim %s: %s", claim.pk, e)


def _notify_worker(claim, event_type: str):
    """Queue a WhatsApp / email notification to the worker."""
    try:
        from apps.notifications.tasks import send_claim_notification
        send_claim_notification.delay(claim.pk, event_type)
    except Exception as e:
        logger.warning(
            "[process_claims] Could not queue %s notification for claim %s: %s",
            event_type, claim.pk, e,
        )


# ── FraudFlag DB writer ───────────────────────────────────────────────────────

def _write_flag_records(claim, flags: list):
    """
    Persist each flag as a FraudFlag model instance.
    Skips if records already exist for this claim (idempotent).
    """
    try:
        existing_flags = FraudFlag.objects.filter(claim=claim, is_deleted=False)
        for existing in existing_flags:
            existing.soft_delete()

        records = []
        for f in flags:
            records.append(FraudFlag(
                claim             = claim,
                layer             = f.get('layer', 0),
                flag_type         = f.get('flag', 'heuristic')[:30],
                score_contribution = f.get('score_contribution', 0.0),
                detail            = f.get('detail', ''),
            ))
        if records:
            FraudFlag.objects.bulk_create(records, ignore_conflicts=True)
    except Exception as e:
        logger.error("[FraudFlag] Failed to write flag records for claim %s: %s", claim.pk, e, exc_info=True)


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _heuristic_score(claim, flags: list) -> float:
    """Used when ML models are unavailable."""
    score = 0.10

    # No KYC
    try:
        if claim.worker.kyc.status != 'verified':
            score += 0.15
            flags.append({
                'layer': 4, 'flag': 'no_kyc',
                'detail': 'Worker KYC is not verified — heuristic penalty applied.',
                'score_contribution': 0.15,
            })
    except Exception:
        pass

    # High recent claim frequency
    from django.utils import timezone
    from datetime import timedelta
    from apps.claims.models import Claim
    velocity = Claim.objects.filter(
        worker=claim.worker,
        created_at__gte=timezone.now() - timedelta(days=7),
    ).exclude(pk=claim.pk).count()

    if velocity > 3:
        contribution = min(0.30, velocity * 0.05)
        score += contribution
        flags.append({
            'layer': 4, 'flag': 'high_velocity',
            'detail': f"{velocity} claims in last 7 days — heuristic penalty.",
            'score_contribution': contribution,
        })

    flags.append({
        'layer': 4, 'flag': 'heuristic',
        'detail': f"ML models unavailable — heuristic score: {score:.4f}",
        'score_contribution': score,
    })
    return round(min(score, 1.0), 4)
