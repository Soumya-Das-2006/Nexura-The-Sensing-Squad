"""
apps/claims/pipeline.py

6-Layer Fraud Detection Pipeline
==================================
Each layer either PASSES the claim, HOLDS it, or REJECTS it outright.
Layers run in order — a rejection at any layer short-circuits the rest.

Layer 1 — Parametric Gate
    Was there a verified DisruptionEvent in the worker's zone?

Layer 2 — Duplicate Prevention
    unique_together(worker, disruption_event) enforced at DB level.
    We check here before even creating the Claim row.

Layer 3 — GPS Zone Validation
    Is the worker's last-known location within the zone boundary?
    (Radius check using zone.lat/lng + zone.radius_km)

Layer 4 — Isolation Forest ML Score
    Load fraud_iso_forest.pkl → predict anomaly score for this claim's features.
    Combined with XGBoost score from fraud_xgboost.json.

Layer 5 — Score-Based Routing
    score < 0.50  → auto-approve
    0.50–0.70     → on_hold (manual review)
    score > 0.70  → auto-reject

Layer 6 — Nightly Batch Rescan
    daily_batch_fraud_scan task re-evaluates approved claims with the
    Isolation Forest to catch patterns missed in real-time.
    (That task lives in fraud/tasks.py — Step 13)

Returns
-------
result = {
    'decision':        'approve' | 'hold' | 'reject',
    'fraud_score':     float,       # 0.0–1.0
    'flags':           list[dict],  # audit trail
    'rejection_reason': str,
}
"""
import logging
import math
from django.conf import settings
from apps.fraud.service import run_fraud_pipeline
logger = logging.getLogger(__name__)

# ─── ML model cache (loaded once per worker process) ─────────────────────────
_iso_forest  = None
_xgb_model   = None
_feature_cols = None


def _load_fraud_models():
    """Lazy-load fraud ML models from disk. Cache in module globals."""
    global _iso_forest, _xgb_model, _feature_cols
    if _iso_forest is not None:
        return

    models_dir = settings.ML_MODELS_DIR
    try:
        import joblib
        import pandas as pd
        import json

        iso_path  = models_dir / 'fraud_iso_forest.pkl'
        xgb_path  = models_dir / 'fraud_xgboost.json'
        cols_path = models_dir / 'fraud_feature_cols.csv'

        if iso_path.exists():
            _iso_forest = joblib.load(iso_path)
            logger.info("[fraud] Isolation Forest loaded from %s", iso_path)

        if xgb_path.exists():
            import xgboost as xgb
            _xgb_model = xgb.XGBClassifier()
            _xgb_model.load_model(str(xgb_path))
            logger.info("[fraud] XGBoost fraud model loaded from %s", xgb_path)

        if cols_path.exists():
            _feature_cols = pd.read_csv(cols_path)['feature'].tolist()

    except Exception as e:
        logger.warning("[fraud] Could not load ML models: %s — using heuristic fallback.", e)


# ─── Main pipeline entry point ────────────────────────────────────────────────

def run_fraud_pipeline(claim) -> dict:
    """
    Run all 6 layers of fraud detection on a Claim instance.
    The Claim must already be saved (we need its pk for logging).

    Returns a result dict — caller is responsible for updating the Claim.
    """
    flags  = []
    result = {
        'decision':         'approve',
        'fraud_score':      0.0,
        'flags':            flags,
        'rejection_reason': '',
    }

    worker = claim.worker
    event  = claim.disruption_event
    policy = claim.policy

    # ── Layer 1: Parametric Gate ─────────────────────────────────────────
    if not event or not event.is_full_trigger:
        if event and not event.is_full_trigger:
            # Partial trigger — reduce payout to 50%, still valid
            flags.append({
                'layer': 1, 'flag': 'partial_trigger',
                'detail': 'Severity below full-payout threshold — 50% payout applied.',
                'score_contribution': 0.05,
            })
        else:
            result['decision']         = 'reject'
            result['rejection_reason'] = 'No qualifying disruption event found for your zone.'
            flags.append({
                'layer': 1, 'flag': 'no_event',
                'detail': 'Parametric gate failed — no verified disruption event.',
                'score_contribution': 1.0,
            })
            result['flags'] = flags
            return result

    # ── Layer 2: Duplicate Prevention ───────────────────────────────────
    from apps.claims.models import Claim
    duplicate = Claim.objects.filter(
        worker=worker,
        disruption_event=event,
    ).exclude(pk=claim.pk).exists()

    if duplicate:
        result['decision']         = 'reject'
        result['rejection_reason'] = 'Duplicate claim — you already have a claim for this event.'
        flags.append({
            'layer': 2, 'flag': 'duplicate',
            'detail': 'A claim for this disruption event already exists for this worker.',
            'score_contribution': 1.0,
        })
        result['flags'] = flags
        return result

    # ── Layer 3: GPS Zone Validation ─────────────────────────────────────
    zone = event.zone
    try:
        worker_profile  = worker.workerprofile
        worker_zone     = worker_profile.zone

        if worker_zone and worker_zone.pk != zone.pk:
            # Worker's registered zone differs from the event zone
            flags.append({
                'layer': 3, 'flag': 'zone_mismatch',
                'detail': (
                    f"Worker registered in {worker_zone} but event in {zone}. "
                    "Flagging for review."
                ),
                'score_contribution': 0.30,
            })
            # Don't reject — hold for review
    except Exception:
        flags.append({
            'layer': 3, 'flag': 'zone_check_skipped',
            'detail': 'Worker profile not found — zone check skipped.',
            'score_contribution': 0.05,
        })

    # ── Layer 4: ML Fraud Score ──────────────────────────────────────────
    ml_score = _compute_ml_score(claim, event, flags)
    result['fraud_score'] = ml_score

    # ── Layer 5: Score-Based Routing ─────────────────────────────────────
    if ml_score >= 0.70:
        result['decision']         = 'reject'
        result['rejection_reason'] = (
            f"Automated fraud detection flagged this claim (score: {ml_score:.2f}). "
            "If you believe this is an error, please contact support."
        )
    elif ml_score >= 0.50:
        result['decision'] = 'hold'
        flags.append({
            'layer': 5, 'flag': 'score_hold',
            'detail': f"Score {ml_score:.2f} is in the review band (0.50–0.70).",
            'score_contribution': ml_score,
        })
    else:
        result['decision'] = 'approve'

    result['flags'] = flags
    return result


# ─── ML score computation ─────────────────────────────────────────────────────

def _compute_ml_score(claim, event, flags: list) -> float:
    """
    Attempt to load and run the Isolation Forest + XGBoost models.
    Falls back to a simple heuristic if models are unavailable.
    """
    _load_fraud_models()

    if _iso_forest is None:
        return _heuristic_score(claim, event, flags)

    try:
        import pandas as pd
        import numpy as np

        features = _build_feature_vector(claim, event)
        df = pd.DataFrame([features])

        # Isolation Forest: convert anomaly score (−1 = anomaly, 1 = normal) to 0–1
        iso_raw   = _iso_forest.score_samples(df)[0]   # more negative = more anomalous
        iso_score = float(1 / (1 + math.exp(iso_raw)))  # sigmoid to 0–1

        xgb_score = 0.0
        if _xgb_model is not None:
            xgb_prob  = _xgb_model.predict_proba(df)[0][1]  # probability of class 1 (fraud)
            xgb_score = float(xgb_prob)

        # Ensemble: 60% XGBoost + 40% Isolation Forest
        combined = 0.6 * xgb_score + 0.4 * iso_score

        flags.append({
            'layer': 4, 'flag': 'ml_score',
            'detail': f"ISO={iso_score:.3f} XGB={xgb_score:.3f} combined={combined:.3f}",
            'score_contribution': combined,
        })
        return round(combined, 4)

    except Exception as e:
        logger.warning("[fraud layer 4] ML scoring failed: %s — using heuristic.", e)
        return _heuristic_score(claim, event, flags)


def _build_feature_vector(claim, event) -> dict:
    """
    Build a feature dict for ML inference.
    Mirrors the feature set used during model training.
    """
    worker  = claim.worker
    profile = getattr(worker, 'workerprofile', None)

    # Past claim velocity (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    from apps.claims.models import Claim
    cutoff = timezone.now() - timedelta(days=30)
    claim_velocity = Claim.objects.filter(
        worker=worker, created_at__gte=cutoff
    ).count()

    return {
        'trigger_type_encoded': {
            'heavy_rain': 0, 'extreme_heat': 1, 'severe_aqi': 2,
            'flash_flood': 3, 'curfew_strike': 4, 'platform_down': 5,
        }.get(event.trigger_type, 0),
        'severity_value':       event.severity_value,
        'threshold_value':      event.threshold_value,
        'is_full_trigger':      int(event.is_full_trigger),
        'payout_amount':        float(claim.payout_amount),
        'claim_velocity_30d':   claim_velocity,
        'worker_risk_score':    getattr(profile, 'risk_score', 0.5) if profile else 0.5,
        'zone_risk_multiplier': float(event.zone.risk_multiplier) if event.zone else 1.0,
        'has_kyc':              int(_has_kyc(worker)),
        'platform_encoded': {
            'zomato': 0, 'swiggy': 1, 'amazon': 2,
            'zepto': 3, 'blinkit': 4, 'dunzo': 5, 'other': 6,
        }.get(getattr(profile, 'platform', 'other'), 6) if profile else 6,
    }


def _has_kyc(user) -> bool:
    try:
        return user.kyc.status == 'verified'
    except Exception:
        return False


def _heuristic_score(claim, event, flags: list) -> float:
    """
    Simple rule-based fraud score when ML models are unavailable.
    Used in development and when models fail to load.
    """
    score = 0.1  # baseline

    # Workers without KYC get a higher score
    if not _has_kyc(claim.worker):
        score += 0.15
        flags.append({
            'layer': 4, 'flag': 'no_kyc',
            'detail': 'Worker KYC not verified — heuristic penalty applied.',
            'score_contribution': 0.15,
        })

    # High claim velocity
    from django.utils import timezone
    from datetime import timedelta
    from apps.claims.models import Claim
    cutoff   = timezone.now() - timedelta(days=7)
    velocity = Claim.objects.filter(worker=claim.worker, created_at__gte=cutoff).count()
    if velocity > 3:
        score += 0.20
        flags.append({
            'layer': 4, 'flag': 'high_velocity',
            'detail': f"{velocity} claims in last 7 days.",
            'score_contribution': 0.20,
        })

    flags.append({
        'layer': 4, 'flag': 'heuristic_score',
        'detail': f"ML models unavailable — heuristic score used: {score:.3f}",
        'score_contribution': score,
    })
    return round(min(score, 1.0), 4)
