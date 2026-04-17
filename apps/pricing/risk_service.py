"""
apps/pricing/risk_service.py

Single-responsibility service for XGBoost risk scoring.
Loads the calibrated sklearn pipeline once per process (module-level cache).
Exposes one public function: predict_risk_score(worker_profile) -> float
"""
import json
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Module-level cache (loaded once per process) ──────────────────────────────
_pipeline      = None   # CalibratedClassifierCV wrapping XGBClassifier
_feature_list  = None   # list[str], 44 names in exact training order
_metadata      = None   # dict — pricing constants
_loaded        = False

BASE_PREMIUM   = 150.0
MAX_MULTIPLIER = 3.0


def _load() -> bool:
    """
    Lazy-load models from settings.ML_MODELS_DIR.
    Idempotent — safe to call multiple times.
    Returns True on success.
    """
    global _pipeline, _feature_list, _metadata, _loaded
    global BASE_PREMIUM, MAX_MULTIPLIER

    if _loaded:
        return True

    models_dir: Path = settings.ML_MODELS_DIR

    try:
        import joblib

        pkl = models_dir / "risk_model.pkl"
        if not pkl.exists():
            logger.error("[risk] risk_model.pkl not found at %s", pkl)
            return False

        _pipeline = joblib.load(pkl)
        logger.info("[risk] Pipeline loaded: %s", type(_pipeline).__name__)

        feat = models_dir / "feature_list.json"
        if feat.exists():
            with open(feat) as f:
                _feature_list = json.load(f)
            logger.info("[risk] %d features loaded", len(_feature_list))

        meta = models_dir / "model_metadata.json"
        if meta.exists():
            with open(meta) as f:
                _metadata = json.load(f)
            pricing = _metadata.get("pricing", {})
            BASE_PREMIUM   = float(pricing.get("base_premium_inr", 150))
            MAX_MULTIPLIER = float(pricing.get("max_multiplier", 3.0))

        _loaded = _pipeline is not None
        return _loaded

    except ImportError as exc:
        logger.error("[risk] Missing library: %s", exc)
        return False
    except Exception as exc:
        logger.error("[risk] Load error: %s", exc, exc_info=True)
        return False


def is_available() -> bool:
    return _loaded and _pipeline is not None


# ── Feature engineering ───────────────────────────────────────────────────────

def _build_features(profile) -> dict:
    """
    Build the 44-feature dict from a WorkerProfile instance.
    All fallbacks are explicit — no silent NaN values.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.claims.models import Claim

    user  = profile.user
    zone  = profile.zone
    now   = timezone.now()
    today = now.date()

    # ── Tenure ────────────────────────────────────────────────────────────
    tenure_months = max((today - user.date_joined.date()).days / 30.0, 0)

    # ── Payout history (earnings proxy) ──────────────────────────────────
    total_payout_yr = float(sum(
        p.amount for p in user.payouts.filter(
            status="credited",
            credited_at__gte=now - timedelta(days=365),
        )
    ))

    # ── Claim history ─────────────────────────────────────────────────────
    all_claims  = Claim.objects.filter(worker=user)
    claim_count = all_claims.count()
    claims_6m   = all_claims.filter(
        created_at__gte=now - timedelta(days=180)
    ).count()
    last_claim      = all_claims.order_by("-created_at").first()
    last_claim_days = (
        (today - last_claim.created_at.date()).days if last_claim else 999
    )

    # ── Zone historical events ────────────────────────────────────────────
    rain_events = heat_events = flood_freq = curfew_count = 0
    zone_events_yr = 0

    if zone:
        from apps.triggers.models import DisruptionEvent
        qs = DisruptionEvent.objects.filter(
            zone=zone, started_at__gte=now - timedelta(days=365)
        )
        zone_events_yr = qs.count()
        rain_events    = qs.filter(trigger_type="heavy_rain").count()
        heat_events    = qs.filter(trigger_type="extreme_heat").count()
        flood_freq     = qs.filter(trigger_type="flash_flood").count()
        curfew_count   = qs.filter(trigger_type="curfew_strike").count()

    zone_risk_enc = float(zone.risk_multiplier) if zone else 1.0

    # ── Calendar ──────────────────────────────────────────────────────────
    month      = today.month
    is_monsoon = int(month in (6, 7, 8, 9))

    # ── Forecast features ─────────────────────────────────────────────────
    rain_mm = max_temp = aqi_fcst = 0.0
    max_temp = 32.0
    aqi_fcst = 100.0

    if zone:
        try:
            fc = zone.forecasts.order_by("-generated_at").first()
            if fc:
                rain_mm  = float(fc.rain_probability) * 50
                aqi_fcst = float(fc.aqi_probability)  * 300
                max_temp = 38.0 if float(fc.heat_probability) > 0.5 else 30.0
        except Exception:
            pass

    # ── Derived scores ────────────────────────────────────────────────────
    import math
    weather_stress = round(
        0.4 * min(rain_mm / 35.0, 1.0)
        + 0.3 * min(max(max_temp - 35.0, 0) / 7.0, 1.0)
        + 0.3 * min(aqi_fcst / 300.0, 1.0), 4
    )
    earnings_vuln   = round(min(total_payout_yr / 50000.0, 1.0), 4)
    experience_risk = round(max(1.0 - tenure_months / 24.0, 0.0), 4)
    zone_hazard     = round(min(zone_events_yr / 20.0, 1.0), 4)
    claim_recency   = round(1.0 / max(last_claim_days / 30.0, 1.0), 4)

    # ── Platform one-hot ──────────────────────────────────────────────────
    platform = profile.platform or "other"
    seg_food  = int(platform in ("zomato", "swiggy"))
    seg_ecomm = int(platform in ("amazon",))
    seg_groc  = int(platform in ("zepto", "blinkit", "dunzo"))

    # ── City tier ─────────────────────────────────────────────────────────
    TIER1 = {"Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Kolkata"}
    TIER2 = {"Pune"}
    city  = zone.city if zone else ""
    t1 = int(city in TIER1)
    t2 = int(city in TIER2)
    t3 = int(city not in TIER1 and city not in TIER2)

    # ── Vehicle type ──────────────────────────────────────────────────────
    seg     = profile.segment or "bike"
    v_bike  = int(seg == "bike")
    v_bicy  = int(seg == "bicycle")
    v_car   = int(seg == "car")

    return {
        "tenure_months":                    round(tenure_months, 2),
        "average_daily_earnings":           600.0,
        "active_hours_per_day":             8.0,
        "historical_rain_events":           rain_events,
        "historical_heat_events":           heat_events,
        "average_aqi":                      100.0,
        "flood_frequency":                  flood_freq,
        "curfew_incidents":                 curfew_count,
        "month":                            month,
        "is_monsoon_week":                  is_monsoon,
        "forecasted_rain_mm":               round(rain_mm, 2),
        "forecasted_max_temp_c":            round(max_temp, 2),
        "forecasted_aqi":                   round(aqi_fcst, 2),
        "flood_alert_level":                0,
        "curfew_flag":                      0,
        "past_claim_count":                 claim_count,
        "claim_frequency_last_6m":          claims_6m,
        "last_claim_days_ago":              last_claim_days,
        "total_payout_last_year":           round(total_payout_yr, 2),
        "zone_risk_encoded":                zone_risk_enc,
        "weather_stress_index":             weather_stress,
        "earnings_vulnerability":           earnings_vuln,
        "experience_risk_factor":           experience_risk,
        "zone_hazard_score":                zone_hazard,
        "claim_recency_weight":             claim_recency,
        "extreme_heat_flag":                int(max_temp > 42),
        "severe_aqi_flag":                  int(aqi_fcst > 300),
        "heavy_rain_flag":                  int(rain_mm > 35),
        "delivery_segment_ecommerce":       seg_ecomm,
        "delivery_segment_food":            seg_food,
        "delivery_segment_grocery":         seg_groc,
        "season_monsoon":                   int(month in (6, 7, 8, 9)),
        "season_spring":                    int(month in (3, 4, 5)),
        "season_summer":                    int(month in (4, 5, 6)),
        "season_winter":                    int(month in (11, 12, 1, 2)),
        "city_tier_tier1":                  t1,
        "city_tier_tier2":                  t2,
        "city_tier_tier3":                  t3,
        "vehicle_type_bicycle":             v_bicy,
        "vehicle_type_car":                 v_car,
        "vehicle_type_motorcycle":          v_bike,
        "weekday_pattern_mixed":            1,
        "weekday_pattern_weekday_heavy":    0,
        "weekday_pattern_weekend_heavy":    0,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def predict_risk_score(profile) -> float:
    """
    Compute disruption probability for a WorkerProfile.

    Returns
    -------
    float in [0.0, 1.0]
    Falls back to zone.risk_multiplier / 3.0 if models unavailable.
    """
    if not is_available():
        _load()

    if not is_available():
        zone = profile.zone
        fallback = float(zone.risk_multiplier) / MAX_MULTIPLIER if zone else 0.5
        logger.warning("[risk] Model unavailable — using fallback %.3f", fallback)
        return round(min(fallback, 1.0), 4)

    try:
        import pandas as pd

        features = _build_features(profile)
        df = pd.DataFrame([features])

        if _feature_list:
            for col in _feature_list:
                if col not in df.columns:
                    df[col] = 0
            df = df[_feature_list]

        try:
            prob = float(_pipeline.predict_proba(df)[0][1])
        except (ValueError, AttributeError):
            prob = float(_pipeline.predict(df)[0])
        return round(max(0.0, min(1.0, prob)), 4)

    except Exception as exc:
        logger.error("[risk] Inference error: %s", exc, exc_info=True)
        zone = profile.zone
        return round(
            min(float(zone.risk_multiplier) / MAX_MULTIPLIER, 1.0) if zone else 0.5,
            4
        )


def calculate_premium(risk_score: float, plan_base_premium: float) -> float:
    """
    Convert risk_score → weekly premium (₹).
    Clamped to [plan_base × 0.80, plan_base × 1.50].
    """
    raw   = BASE_PREMIUM * (1.0 + risk_score * (MAX_MULTIPLIER - 1.0))
    low   = plan_base_premium * 0.80
    high  = plan_base_premium * 1.50
    return round(max(low, min(high, raw)), 2)