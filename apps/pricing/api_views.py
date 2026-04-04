"""
apps/pricing/api_views.py
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response

from .loader import (
    load_models, models_available,
    predict_risk_score, calculate_premium,
    BASE_PREMIUM_INR, MAX_MULTIPLIER, _metadata,
)
from .views import _estimate_risk_for_zone, _risk_label

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_risk(request):
    """Current worker's risk score and personalised premium for each plan."""
    if not request.user.is_worker:
        return Response({'error': 'Workers only.'}, status=403)

    try:
        profile = request.user.workerprofile
    except Exception:
        return Response({'error': 'Profile not found.'}, status=404)

    from apps.policies.models import PlanTier
    if not models_available():
        load_models()

    forecast = None
    if profile.zone:
        try:
            forecast = profile.zone.forecasts.order_by('-generated_at').first()
        except Exception:
            pass

    risk_score = predict_risk_score(profile, forecast)
    plans      = PlanTier.objects.filter(is_active=True).order_by('sort_order')

    premiums = {
        plan.slug: calculate_premium(risk_score, float(plan.base_premium))
        for plan in plans
    }

    return Response({
        'risk_score':     risk_score,
        'risk_label':     profile.risk_label,
        'risk_updated_at': profile.risk_updated_at,
        'premiums':       premiums,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_api(request):
    """Public estimate — no login required."""
    from apps.policies.models import PlanTier

    zone_id  = request.data.get('zone_id')
    platform = request.data.get('platform', 'zomato')
    segment  = request.data.get('segment', 'bike')

    risk_score = _estimate_risk_for_zone(zone_id, platform, segment)
    plans      = PlanTier.objects.filter(is_active=True).order_by('sort_order')

    return Response({
        'risk_score': risk_score,
        'risk_label': _risk_label(risk_score),
        'premiums':   {
            plan.slug: calculate_premium(risk_score, float(plan.base_premium))
            for plan in plans
        },
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def model_info(request):
    """Return XGBoost model metadata — admin only."""
    return Response({
        'models_loaded':  models_available(),
        'base_premium':   BASE_PREMIUM_INR,
        'max_multiplier': MAX_MULTIPLIER,
        'metadata':       _metadata,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def trigger_recalculation(request):
    """Admin: trigger manual recalculation for one or all workers."""
    from .tasks import recalculate_all_premiums, recalculate_single_worker

    worker_id = request.data.get('worker_id')
    if worker_id:
        recalculate_single_worker.delay(int(worker_id))
        return Response({'message': f'Recalculation queued for worker {worker_id}.'})

    recalculate_all_premiums.delay()
    return Response({'message': 'Full recalculation task queued.'})
