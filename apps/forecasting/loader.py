"""
apps/forecasting/loader.py

Prophet model loader and inference engine.

Models available (27 .pkl files in ml_models/prophet/):
  prophet_{city}_{metric}.pkl
  city   : bangalore, chennai, delhi, hyderabad, kolkata, mumbai, pune
  metric : aqi, disruption_prob, rainfall_mm, temperature_c

Note: kolkata_rainfall_mm is missing from the training set — we fall back
to the zone's historical rain average for that city.

Usage
-----
  from apps.forecasting.loader import load_all_models, forecast_city_week

  load_all_models()   # call once at startup
  result = forecast_city_week('Mumbai', next_monday)
  # returns ForecastResult dataclass
"""
import logging
import pickle
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Dict

from django.conf import settings

logger = logging.getLogger(__name__)

# ── City name → model file key mapping ───────────────────────────────────────
CITY_KEY_MAP = {
    'Mumbai':    'mumbai',
    'Delhi':     'delhi',
    'Bangalore': 'bangalore',
    'Chennai':   'chennai',
    'Hyderabad': 'hyderabad',
    'Kolkata':   'kolkata',
    'Pune':      'pune',
}

METRICS = ['aqi', 'disruption_prob', 'rainfall_mm', 'temperature_c']

# ── Disruption thresholds (mirrors triggers/thresholds.py) ────────────────────
RAIN_THRESHOLD  = 35.0   # mm/hr
HEAT_THRESHOLD  = 42.0   # °C
AQI_THRESHOLD   = 300.0

# ── Module-level model cache: {city_key: {metric: Prophet}} ──────────────────
_models: Dict[str, Dict[str, object]] = {}
_loaded = False
_load_attempted = False


@dataclass
class ForecastResult:
    city:                  str
    forecast_date:         date
    rain_probability:      float = 0.0
    heat_probability:      float = 0.0
    aqi_probability:       float = 0.0
    disruption_probability: float = 0.0
    forecasted_rain_mm:    float = 0.0
    forecasted_temp_c:     float = 30.0
    forecasted_aqi:        float = 100.0
    overall_risk_level:    str = 'Low'
    model_used:            bool = False   # False if heuristic fallback was used


def load_all_models() -> bool:
    """
    Load all available Prophet .pkl files into the module cache.
    Idempotent — safe to call multiple times.
    Returns True if at least one model loaded successfully.
    """
    global _models, _loaded, _load_attempted

    if _load_attempted:
        return _loaded

    _load_attempted = True

    prophet_dir: Path = settings.ML_MODELS_DIR / 'prophet'
    if not prophet_dir.exists():
        logger.error("[forecasting] Prophet model directory not found: %s", prophet_dir)
        return False

    loaded_count = 0
    failed_count = 0

    for city_display, city_key in CITY_KEY_MAP.items():
        _models[city_key] = {}
        for metric in METRICS:
            fname = prophet_dir / f"prophet_{city_key}_{metric}.pkl"
            if fname.exists():
                try:
                    with open(fname, 'rb') as f:
                        _models[city_key][metric] = pickle.load(f)
                    loaded_count += 1
                except Exception as exc:
                    failed_count += 1
                    logger.warning("[forecasting] Failed to load %s: %s", fname.name, exc)
            else:
                logger.debug("[forecasting] Model not found (will use fallback): %s", fname.name)

    _loaded = loaded_count > 0
    logger.info(
        "[forecasting] Loaded %d Prophet models for %d cities.",
        loaded_count, len(CITY_KEY_MAP),
    )
    if failed_count:
        logger.warning(
            "[forecasting] %d model file(s) failed to load; heuristic fallback will be used where needed.",
            failed_count,
        )
    return _loaded


def models_available() -> bool:
    return _loaded and bool(_models)


def forecast_city_week(city: str, week_start: date) -> ForecastResult:
    """
    Generate a one-week disruption forecast for a city.

    Parameters
    ----------
    city       : Display name ('Mumbai', 'Delhi', …)
    week_start : The Monday date of the target week

    Returns a ForecastResult with probabilities and risk level.
    """
    if not _load_attempted:
        load_all_models()

    city_key = CITY_KEY_MAP.get(city)
    if not city_key or city_key not in _models:
        logger.warning("[forecasting] No models for city: %s — using heuristic.", city)
        return _heuristic_forecast(city, week_start)

    city_models = _models[city_key]

    # Prophet requires a DataFrame with 'ds' column
    try:
        import pandas as pd
        import numpy as np

        # Build 7-day date range (Mon → Sun)
        dates = [week_start + timedelta(days=i) for i in range(7)]
        future = pd.DataFrame({'ds': pd.to_datetime(dates)})

        def _predict(metric: str) -> Optional[float]:
            """Run one Prophet model and return mean yhat for the week."""
            model = city_models.get(metric)
            if model is None:
                return None
            try:
                fc = model.predict(future)
                return float(np.clip(fc['yhat'].mean(), 0, None))
            except Exception as exc:
                logger.warning("[forecasting] Predict failed (%s %s): %s", city_key, metric, exc)
                return None

        rain_mm    = _predict('rainfall_mm')   # mm/hr
        temp_c     = _predict('temperature_c') # °C
        aqi_val    = _predict('aqi')           # AQI index
        disrupt_p  = _predict('disruption_prob')  # 0–1
        used_model = any(v is not None for v in (rain_mm, temp_c, aqi_val, disrupt_p))

        # ── Convert raw metrics → disruption probabilities ────────────────
        # Use sigmoid-like transform so values near threshold → ~0.5

        rain_prob  = _sigmoid_prob(rain_mm or 0.0, RAIN_THRESHOLD)  if rain_mm  is not None else _city_heuristic_rain(city)
        heat_prob  = _sigmoid_prob(temp_c  or 0.0, HEAT_THRESHOLD)  if temp_c   is not None else 0.1
        aqi_prob   = _sigmoid_prob(aqi_val or 0.0, AQI_THRESHOLD)   if aqi_val  is not None else 0.1
        dis_prob   = float(np.clip(disrupt_p or 0.0, 0.0, 1.0))     if disrupt_p is not None else 0.2

        from .models import ZoneForecast
        risk_level = ZoneForecast.compute_risk_level(rain_prob, heat_prob, aqi_prob, dis_prob)

        return ForecastResult(
            city                  = city,
            forecast_date         = week_start,
            rain_probability      = round(rain_prob, 4),
            heat_probability      = round(heat_prob, 4),
            aqi_probability       = round(aqi_prob, 4),
            disruption_probability= round(dis_prob, 4),
            forecasted_rain_mm    = round(rain_mm or 0.0, 2),
            forecasted_temp_c     = round(temp_c  or 30.0, 2),
            forecasted_aqi        = round(aqi_val or 100.0, 2),
            overall_risk_level    = risk_level,
            model_used            = used_model,
        )

    except ImportError:
        logger.error("[forecasting] pandas/numpy not available — using heuristic.")
        return _heuristic_forecast(city, week_start)

    except Exception as exc:
        logger.error("[forecasting] Forecasting error for %s: %s", city, exc, exc_info=True)
        return _heuristic_forecast(city, week_start)


# ── Math helpers ──────────────────────────────────────────────────────────────

def _sigmoid_prob(value: float, threshold: float, steepness: float = 0.15) -> float:
    """
    Map a raw metric value to [0, 1] using a sigmoid centred at threshold.
    value = threshold → 0.5 probability
    value >> threshold → ~1.0
    value << threshold → ~0.0
    """
    import math
    x = (value - threshold) * steepness
    return round(1.0 / (1.0 + math.exp(-x)), 4)


def _city_heuristic_rain(city: str) -> float:
    """Fallback rain probability based on city's known monsoon risk."""
    rain_risk = {
        'Mumbai':    0.65,
        'Chennai':   0.55,
        'Kolkata':   0.60,
        'Bangalore': 0.35,
        'Hyderabad': 0.40,
        'Delhi':     0.25,
        'Pune':      0.35,
    }
    return rain_risk.get(city, 0.30)


def _heuristic_forecast(city: str, week_start: date) -> ForecastResult:
    """
    Statistical fallback when Prophet models are unavailable.
    Based on city-level seasonal disruption rates.
    """
    month = week_start.month

    # Monsoon months
    is_monsoon = month in (6, 7, 8, 9)
    is_summer  = month in (4, 5, 6)
    is_winter  = month in (11, 12, 1, 2)

    city_rain = _city_heuristic_rain(city)
    city_heat = {
        'Delhi': 0.55, 'Mumbai': 0.20, 'Chennai': 0.35,
        'Kolkata': 0.25, 'Hyderabad': 0.30, 'Bangalore': 0.10, 'Pune': 0.20,
    }.get(city, 0.20)
    city_aqi = {
        'Delhi': 0.60, 'Mumbai': 0.25, 'Kolkata': 0.40,
        'Chennai': 0.20, 'Hyderabad': 0.25, 'Bangalore': 0.15, 'Pune': 0.20,
    }.get(city, 0.20)

    rain_prob = city_rain * (1.5 if is_monsoon else 0.4)
    heat_prob = city_heat * (1.5 if is_summer else 0.5)
    aqi_prob  = city_aqi  * (1.5 if is_winter else 0.6)
    dis_prob  = round(max(rain_prob, heat_prob, aqi_prob) * 0.8, 4)

    rain_prob = round(min(rain_prob, 1.0), 4)
    heat_prob = round(min(heat_prob, 1.0), 4)
    aqi_prob  = round(min(aqi_prob,  1.0), 4)

    from .models import ZoneForecast
    risk_level = ZoneForecast.compute_risk_level(rain_prob, heat_prob, aqi_prob, dis_prob)

    return ForecastResult(
        city=city, forecast_date=week_start,
        rain_probability=rain_prob, heat_probability=heat_prob,
        aqi_probability=aqi_prob, disruption_probability=dis_prob,
        forecasted_rain_mm=rain_prob * 40, forecasted_temp_c=35.0,
        forecasted_aqi=aqi_prob * 300,
        overall_risk_level=risk_level, model_used=False,
    )


# ── Utility — re-exported here so other modules can import from loader ────────

def _next_monday(ref=None):
    """Return the date of the next Monday (or next week's Monday if today is Monday)."""
    from datetime import date, timedelta
    today = ref or date.today()
    days = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days)
