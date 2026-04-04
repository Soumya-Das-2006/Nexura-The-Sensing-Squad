"""
apps/pricing/views.py

/calculator/  → Public premium calculator (AJAX endpoint + web page)
"""
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class PremiumCalculatorView(View):
    """
    Public page — lets prospective workers estimate their weekly premium
    before registering.
    """
    template_name = 'pricing/calculator.html'

    def get(self, request):
        from apps.zones.models import Zone
        zones = Zone.objects.filter(active=True).order_by('city', 'area_name')
        return render(request, self.template_name, {'zones': zones})


class CalculatePremiumAjax(View):
    """
    POST /api/v1/pricing/calculate/
    Body: { zone_id, platform, segment, plan_slug }
    Returns: { basic, standard, premium, risk_score }
    """

    def post(self, request):
        import json
        from apps.zones.models import Zone
        from apps.policies.models import PlanTier
        from .loader import load_models, models_available, predict_risk_score, calculate_premium

        try:
            data     = json.loads(request.body)
            zone_id  = data.get('zone_id')
            platform = data.get('platform', 'zomato')
            segment  = data.get('segment', 'bike')
        except Exception:
            return JsonResponse({'error': 'Invalid request body.'}, status=400)

        # Build a lightweight fake profile for the calculator
        risk_score = _estimate_risk_for_zone(zone_id, platform, segment)

        plans = PlanTier.objects.filter(is_active=True).order_by('sort_order')
        result = {
            'risk_score':  risk_score,
            'risk_label':  _risk_label(risk_score),
            'premiums':    {},
        }
        for plan in plans:
            result['premiums'][plan.slug] = calculate_premium(
                risk_score, float(plan.base_premium)
            )

        return JsonResponse(result)


def _estimate_risk_for_zone(zone_id, platform: str, segment: str) -> float:
    """
    Quick risk estimate for the calculator — no Worker object needed.
    Uses zone.risk_multiplier and a simple heuristic.
    """
    from apps.zones.models import Zone
    from .loader import BASE_PREMIUM_INR, MAX_MULTIPLIER

    base_risk = 0.3   # default if zone unknown

    try:
        zone      = Zone.objects.get(pk=zone_id)
        base_risk = float(zone.risk_multiplier - 1.0) / (MAX_MULTIPLIER - 1.0)
        base_risk = max(0.0, min(1.0, base_risk))
    except Exception:
        pass

    # Platform adjustment
    platform_adj = {
        'zomato': 0.0, 'swiggy': 0.0,
        'amazon': -0.05, 'zepto': -0.02,
        'blinkit': -0.02, 'dunzo': 0.0,
    }.get(platform, 0.0)

    # Segment adjustment
    segment_adj = {
        'bike': 0.0, 'bicycle': 0.05,
        'auto': -0.03, 'car': -0.05,
    }.get(segment, 0.0)

    return round(max(0.0, min(1.0, base_risk + platform_adj + segment_adj)), 4)


def _risk_label(score: float) -> str:
    if score >= 0.75:
        return 'High'
    elif score >= 0.50:
        return 'Moderate'
    elif score >= 0.25:
        return 'Low'
    return 'Minimal'
