"""
apps/forecasting/forecast_service.py

Clean Prophet forecast service.
Uses city subfolder structure exclusively:
  ml_models/prophet/{city}/prophet_{city}_{metric}.pkl

Supported cities:  mumbai, delhi, bangalore, chennai,
                   hyderabad, kolkata, pune
Supported metrics: aqi, rainfall_mm, temperature_c, disruption_prob

Models are loaded on first request and cached per (city, metric).
"""
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Cache: (city, metric) -> Prophet model ────────────────────────────────────
_model_cache: dict = {}
_load_attempted: set = set()

SUPPORTED_CITIES = {
    "mumbai", "delhi", "bangalore", "chennai",
    "hyderabad", "kolkata", "pune",
}

SUPPORTED_METRICS = {
    "aqi", "rainfall_mm", "temperature_c", "disruption_prob",
}


def _model_path(city: str, metric: str) -> Path:
    """
    Returns the canonical path for a Prophet model file.
    Uses city subfolder structure only.
    """
    base: Path = settings.ML_MODELS_DIR
    city = city.lower().replace(" ", "_")
    return base / "prophet" / city / f"prophet_{city}_{metric}.pkl"


def _load_model(city: str, metric: str):
    """
    Load a single Prophet model into cache.
    Returns the model or None if file not found / load fails.
    """
    key = (city, metric)

    if key in _model_cache:
        return _model_cache[key]

    if key in _load_attempted:
        return None  # Already tried and failed — don't retry

    _load_attempted.add(key)
    path = _model_path(city, metric)

    if not path.exists():
        logger.warning("[forecast] Model not found: %s", path)
        return None

    try:
        import joblib
        model = joblib.load(path)
        _model_cache[key] = model
        logger.info("[forecast] Loaded %s/%s", city, metric)
        return model
    except Exception as exc:
        logger.error("[forecast] Failed to load %s/%s: %s", city, metric, exc)
        return None


def is_available(city: str, metric: str) -> bool:
    """Check if a specific model is available without loading it."""
    return _model_path(city, metric).exists()


# ── Public API ────────────────────────────────────────────────────────────────

def get_forecast(city: str, metric: str, days: int = 7) -> dict:
    """
    Generate a forecast for a city/metric pair.

    Parameters
    ----------
    city   : one of SUPPORTED_CITIES
    metric : one of SUPPORTED_METRICS
    days   : number of days to forecast (default 7)

    Returns
    -------
    dict with keys:
        city, metric, days,
        forecast: list of {ds, yhat, yhat_lower, yhat_upper},
        summary: {mean, min, max},
        available: bool
    """
    city   = city.lower().strip()
    metric = metric.lower().strip()

    base_result = {
        "city":      city,
        "metric":    metric,
        "days":      days,
        "forecast":  [],
        "summary":   {"mean": None, "min": None, "max": None},
        "available": False,
    }

    if city not in SUPPORTED_CITIES:
        logger.warning("[forecast] Unsupported city: %s", city)
        return base_result

    if metric not in SUPPORTED_METRICS:
        logger.warning("[forecast] Unsupported metric: %s", metric)
        return base_result

    model = _load_model(city, metric)
    if model is None:
        return base_result

    try:
        import pandas as pd
        from django.utils import timezone

        # Build future dataframe
        today  = pd.Timestamp(timezone.now().date())
        future = pd.DataFrame({
            "ds": pd.date_range(start=today, periods=days, freq="D")
        })

        forecast_df = model.predict(future)

        cols = ["ds", "yhat", "yhat_lower", "yhat_upper"]
        rows = []
        for _, row in forecast_df[cols].iterrows():
            rows.append({
                "ds":         row["ds"].strftime("%Y-%m-%d"),
                "yhat":       round(float(row["yhat"]), 3),
                "yhat_lower": round(float(row["yhat_lower"]), 3),
                "yhat_upper": round(float(row["yhat_upper"]), 3),
            })

        yhats = [r["yhat"] for r in rows]
        summary = {
            "mean": round(sum(yhats) / len(yhats), 3) if yhats else None,
            "min":  round(min(yhats), 3) if yhats else None,
            "max":  round(max(yhats), 3) if yhats else None,
        }

        return {
            "city":      city,
            "metric":    metric,
            "days":      days,
            "forecast":  rows,
            "summary":   summary,
            "available": True,
        }

    except Exception as exc:
        logger.error(
            "[forecast] Prediction error %s/%s: %s", city, metric, exc,
            exc_info=True,
        )
        return base_result


def get_city_forecast(city: str, days: int = 7) -> dict:
    """
    Get all 4 metrics for a city in one call.
    Returns a dict keyed by metric name.
    """
    return {
        metric: get_forecast(city, metric, days)
        for metric in SUPPORTED_METRICS
    }


def get_disruption_probability(city: str) -> float:
    """
    Convenience function — returns tomorrow's disruption probability.
    Returns 0.5 as fallback if model unavailable.
    """
    result = get_forecast(city, "disruption_prob", days=1)
    if result["available"] and result["forecast"]:
        prob = result["forecast"][0]["yhat"]
        return round(max(0.0, min(1.0, prob)), 4)
    return 0.5
