"""
apps/fraud/loader.py

ML model loader and feature engineering for Nexura's fraud detection.

Trained models (loaded once per worker process):
  fraud_iso_forest.pkl   — sklearn IsolationForest (200 estimators, contamination=0.05)
  fraud_xgboost.json     — XGBClassifier
  fraud_feature_cols.csv — 34 feature names in exact training order
  iso_norm_params.csv    — s_min / s_max for IsolationForest score normalisation

Feature columns (exact order from training):
  claim_amount_inr, claim_frequency_last_30_days, claim_frequency_last_6_months,
  claim_hour, event_type_encoded, gps_distance_from_event_km, gps_missing_flag,
  number_of_devices_used, worker_online_status_during_event,
  claim_submission_delay_hours, claims_filed_within_1hr, same_device_multiple_workers,
  shared_bank_account_flag, referral_cluster_size, zone_claim_density,
  tenure_months, account_age_days, worker_rating, is_odd_hour, is_weekend,
  instant_claim_flag, very_fast_claim, claim_velocity_ratio, gps_far_from_zone,
  gps_very_far, device_shared_risk, claim_amount_zscore, high_amount_flag,
  network_fraud_risk, fraud_signal_composite, trust_score,
  delivery_segment_food, delivery_segment_ecommerce, delivery_segment_grocery
"""
import logging
import math
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Module-level model cache (loaded once per process) ────────────────────────
_iso_forest    = None
_xgb_model     = None
_feature_cols  = None   # list[str] in exact training order
_iso_s_min     = None
_iso_s_max     = None
_models_loaded = False


def load_models() -> bool:
    """
    Load all fraud ML models from ML_MODELS_DIR.
    Returns True on success, False if any model fails to load.
    Idempotent — safe to call multiple times.
    """
    global _iso_forest, _xgb_model, _feature_cols, _iso_s_min, _iso_s_max, _models_loaded

    if _models_loaded:
        return True

    models_dir = settings.ML_MODELS_DIR

    try:
        import joblib
        import pandas as pd
        import xgboost as xgb

        # ── IsolationForest ───────────────────────────────────────────────
        iso_path = models_dir / 'fraud_iso_forest.pkl'
        if iso_path.exists():
            _iso_forest = joblib.load(iso_path)
            logger.info("[fraud] IsolationForest loaded (%d estimators)", _iso_forest.n_estimators)
        else:
            logger.warning("[fraud] fraud_iso_forest.pkl not found at %s", iso_path)

        # ── XGBoost ───────────────────────────────────────────────────────
        xgb_path = models_dir / 'fraud_xgboost.json'
        if xgb_path.exists():
            _xgb_model = xgb.XGBClassifier()
            _xgb_model.load_model(str(xgb_path))
            logger.info("[fraud] XGBoost fraud model loaded")
        else:
            logger.warning("[fraud] fraud_xgboost.json not found at %s", xgb_path)

        # ── Feature columns ───────────────────────────────────────────────
        cols_path = models_dir / 'fraud_feature_cols.csv'
        if cols_path.exists():
            df = pd.read_csv(cols_path, header=None)
            # Handle both "feature" header and headerless CSV
            if df.iloc[0, 0] == 'feature':
                _feature_cols = df.iloc[1:, 0].tolist()
            else:
                _feature_cols = df.iloc[:, 0].tolist()
            logger.info("[fraud] Feature columns loaded (%d features)", len(_feature_cols))
        else:
            logger.warning("[fraud] fraud_feature_cols.csv not found")

        # ── IsolationForest normalisation params ──────────────────────────
        norm_path = models_dir / 'iso_norm_params.csv'
        if norm_path.exists():
            norm_df = pd.read_csv(norm_path, index_col=0)
            _iso_s_min = float(norm_df.loc['s_min', 'value'])
            _iso_s_max = float(norm_df.loc['s_max', 'value'])
            logger.info("[fraud] ISO norm params loaded: s_min=%.4f s_max=%.4f", _iso_s_min, _iso_s_max)

        _models_loaded = (_iso_forest is not None and _xgb_model is not None)
        return _models_loaded

    except ImportError as e:
        logger.error("[fraud] Required ML library missing: %s", e)
        return False
    except Exception as e:
        logger.error("[fraud] Model loading error: %s", e, exc_info=True)
        return False


def models_available() -> bool:
    """Quick check — have models been successfully loaded?"""
    return _models_loaded and _iso_forest is not None


# ── Feature engineering ───────────────────────────────────────────────────────

def build_feature_vector(claim) -> dict:
    """
    Build a feature dict for ML inference from a Claim instance.
    Maps Nexura's claim/worker data to the 34 training features.
    Returns a flat dict with all 34 keys.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.claims.models import Claim as ClaimModel

    worker  = claim.worker
    event   = claim.disruption_event
    profile = getattr(worker, 'workerprofile', None)

    now      = timezone.now()
    filed_at = claim.created_at or now

    # ── Claim velocity ─────────────────────────────────────────────────────
    last_30d = ClaimModel.objects.filter(
        worker=worker,
        created_at__gte=now - timedelta(days=30),
    ).exclude(pk=claim.pk).count()

    last_6m = ClaimModel.objects.filter(
        worker=worker,
        created_at__gte=now - timedelta(days=180),
    ).exclude(pk=claim.pk).count()

    # ── Timing features ────────────────────────────────────────────────────
    claim_hour   = filed_at.hour
    is_odd_hour  = int(claim_hour < 6 or claim_hour > 22)
    is_weekend   = int(filed_at.weekday() >= 5)

    event_start  = event.started_at if event else filed_at
    delay_hours  = max((filed_at - event_start).total_seconds() / 3600, 0)
    instant_flag = int(delay_hours < 0.0833)   # < 5 minutes
    very_fast    = int(delay_hours < 0.5)

    # ── GPS features ───────────────────────────────────────────────────────
    # Worker zone vs event zone distance (simplified: same zone = 0km, different = 5km)
    gps_missing       = 0
    gps_distance_km   = 0.0
    gps_far           = 0
    gps_very_far      = 0

    if profile and event:
        worker_zone = profile.zone
        event_zone  = event.zone
        if worker_zone and event_zone:
            if worker_zone.pk != event_zone.pk:
                # Approximate: different zones → flag distance
                try:
                    gps_distance_km = _haversine(
                        float(worker_zone.lat), float(worker_zone.lng),
                        float(event_zone.lat),  float(event_zone.lng),
                    )
                except Exception:
                    gps_distance_km = 5.0
                gps_far      = int(gps_distance_km > 5.0)
                gps_very_far = int(gps_distance_km > 15.0)
        else:
            gps_missing = 1
    else:
        gps_missing = 1

    # ── KYC / account features ─────────────────────────────────────────────
    kyc_verified = 0
    try:
        kyc_verified = int(worker.kyc.status == 'verified')
    except Exception:
        pass

    tenure_days  = (now.date() - worker.date_joined.date()).days
    tenure_months = max(tenure_days / 30, 0)
    account_days  = tenure_days

    # ── Worker rating (proxy — use risk_score inverted) ────────────────────
    risk_score    = getattr(profile, 'risk_score', 0.5) if profile else 0.5
    worker_rating = round(5.0 * (1.0 - risk_score), 2)   # 0→5, 1→0

    # ── Claim amount zscore ────────────────────────────────────────────────
    # Average weekly coverage across plans is ~₹1,166
    MEAN_COVERAGE = 1166.0
    STD_COVERAGE  = 620.0
    amount_zscore = (float(claim.payout_amount) - MEAN_COVERAGE) / STD_COVERAGE
    high_amount   = int(float(claim.payout_amount) > 1500)

    # ── Zone claim density (claims per zone in last 24h) ───────────────────
    zone_density = 0
    if event and event.zone:
        zone_density = ClaimModel.objects.filter(
            disruption_event__zone=event.zone,
            created_at__gte=now - timedelta(hours=24),
        ).count()

    # ── Claim velocity ratio (worker vs zone average) ─────────────────────
    zone_avg    = max(zone_density, 1)
    velocity_ratio = last_30d / zone_avg

    # ── Delivery segment one-hot ───────────────────────────────────────────
    platform      = getattr(profile, 'platform', 'other') if profile else 'other'
    seg_food      = int(platform in ('zomato', 'swiggy'))
    seg_ecommerce = int(platform in ('amazon',))
    seg_grocery   = int(platform in ('zepto', 'blinkit', 'dunzo'))

    # ── Composite / derived ────────────────────────────────────────────────
    network_risk      = int(last_30d > 5 or gps_very_far)
    fraud_signal      = round(
        0.3 * gps_very_far +
        0.2 * (1 - kyc_verified) +
        0.2 * int(last_30d > 5) +
        0.15 * is_odd_hour +
        0.15 * instant_flag,
        4,
    )
    trust_score = round(max(1.0 - fraud_signal, 0.0), 4)

    # ── Event type encoding ────────────────────────────────────────────────
    event_type_map = {
        'heavy_rain': 0, 'extreme_heat': 1, 'severe_aqi': 2,
        'flash_flood': 3, 'curfew_strike': 4, 'platform_down': 5,
    }
    event_type_enc = event_type_map.get(
        event.trigger_type if event else 'heavy_rain', 0
    )

    return {
        'claim_amount_inr':                float(claim.payout_amount),
        'claim_frequency_last_30_days':    last_30d,
        'claim_frequency_last_6_months':   last_6m,
        'claim_hour':                      claim_hour,
        'event_type_encoded':              event_type_enc,
        'gps_distance_from_event_km':      round(gps_distance_km, 3),
        'gps_missing_flag':                gps_missing,
        'number_of_devices_used':          1,          # default — no device tracking in MVP
        'worker_online_status_during_event': 1,         # assumed online
        'claim_submission_delay_hours':    round(delay_hours, 4),
        'claims_filed_within_1hr':         int(delay_hours < 1.0),
        'same_device_multiple_workers':    0,
        'shared_bank_account_flag':        0,
        'referral_cluster_size':           1,
        'zone_claim_density':              zone_density,
        'tenure_months':                   round(tenure_months, 2),
        'account_age_days':                account_days,
        'worker_rating':                   worker_rating,
        'is_odd_hour':                     is_odd_hour,
        'is_weekend':                      is_weekend,
        'instant_claim_flag':              instant_flag,
        'very_fast_claim':                 very_fast,
        'claim_velocity_ratio':            round(velocity_ratio, 4),
        'gps_far_from_zone':               gps_far,
        'gps_very_far':                    gps_very_far,
        'device_shared_risk':              0,
        'claim_amount_zscore':             round(amount_zscore, 4),
        'high_amount_flag':                high_amount,
        'network_fraud_risk':              network_risk,
        'fraud_signal_composite':          fraud_signal,
        'trust_score':                     trust_score,
        'delivery_segment_food':           seg_food,
        'delivery_segment_ecommerce':      seg_ecommerce,
        'delivery_segment_grocery':        seg_grocery,
    }


def score_claim(claim) -> tuple[float, float, float]:
    """
    Run both ML models on a claim and return (iso_score, xgb_score, combined_score).
    All scores are in range [0.0, 1.0] — higher = more likely fraud.

    Falls back to (0.0, 0.0, 0.0) if models are unavailable.
    """
    if not models_available():
        load_models()

    if not models_available():
        logger.warning("[fraud] Models not available — returning zero scores.")
        return 0.0, 0.0, 0.0

    try:
        import pandas as pd

        features = build_feature_vector(claim)

        # Build DataFrame in exact column order
        df = pd.DataFrame([features])
        if _feature_cols:
            # Ensure all expected columns present, fill missing with 0
            for col in _feature_cols:
                if col not in df.columns:
                    df[col] = 0
            df = df[_feature_cols]

        # ── IsolationForest score ────────────────────────────────────────
        iso_raw = _iso_forest.score_samples(df)[0]
        # Normalise using training min/max; clip to [0, 1]
        if _iso_s_min is not None and _iso_s_max is not None:
            iso_range = _iso_s_max - _iso_s_min
            if iso_range > 0:
                iso_score = float((iso_raw - _iso_s_min) / iso_range)
                iso_score = 1.0 - max(0.0, min(1.0, iso_score))  # invert: anomaly = high
            else:
                iso_score = float(1 / (1 + math.exp(iso_raw)))  # sigmoid fallback
        else:
            iso_score = float(1 / (1 + math.exp(iso_raw)))

        # ── XGBoost score ────────────────────────────────────────────────
        xgb_prob  = _xgb_model.predict_proba(df)[0][1]   # P(fraud)
        xgb_score = float(xgb_prob)

        # ── Ensemble: 60% XGB + 40% ISO ─────────────────────────────────
        combined = round(0.6 * xgb_score + 0.4 * iso_score, 4)

        logger.debug(
            "[fraud] Claim #%s — iso=%.4f xgb=%.4f combined=%.4f",
            claim.pk, iso_score, xgb_score, combined,
        )
        return iso_score, xgb_score, combined

    except Exception as e:
        logger.error("[fraud] Scoring error for claim %s: %s", claim.pk, e, exc_info=True)
        return 0.0, 0.0, 0.0


# ── Geometry helper ───────────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lng) points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
