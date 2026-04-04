"""
apps/workers/api_views.py

REST API endpoints:
  GET   /api/v1/workers/profile/       → current worker profile
  PATCH /api/v1/workers/profile/       → update name/platform/zone/upi
  GET   /api/v1/workers/stats/         → payout & claim totals
  GET   /api/v1/workers/dashboard/     → full dashboard data (mobile app)
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import WorkerProfile
from .serializers import WorkerProfileSerializer, WorkerProfileUpdateSerializer

logger = logging.getLogger(__name__)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def worker_profile(request):
    """
    GET  → return full profile
    PATCH → update allowed fields (name, platform, segment, zone, upi_id)
    """
    try:
        profile = request.user.workerprofile
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Profile not found. Complete registration first.'}, status=404)

    if request.method == 'GET':
        serializer = WorkerProfileSerializer(profile)
        return Response(serializer.data)

    # PATCH
    serializer = WorkerProfileUpdateSerializer(
        profile, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(WorkerProfileSerializer(profile).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_stats(request):
    """
    Summary stats for the current worker:
    total_paid_out, total_claims, approved_claims, active_policy, kyc_status
    """
    user = request.user

    total_paid_out  = 0
    total_claims    = 0
    approved_claims = 0
    active_policy   = None

    try:
        from apps.claims.models import Claim
        qs = Claim.objects.filter(worker=user)
        total_claims    = qs.count()
        approved_claims = qs.filter(status='approved').count()
    except Exception:
        pass

    try:
        total_paid_out = sum(
            p.amount for p in user.payouts.filter(status='credited')
        )
    except Exception:
        pass

    try:
        policy = user.policies.filter(status='active').latest('start_date')
        active_policy = {
            'plan':     policy.plan_tier.name,
            'coverage': policy.weekly_coverage,
            'premium':  policy.weekly_premium,
            'status':   policy.status,
        }
    except Exception:
        pass

    return Response({
        'total_paid_out':  float(total_paid_out),
        'total_claims':    total_claims,
        'approved_claims': approved_claims,
        'active_policy':   active_policy,
        'kyc_status':      user.kyc.status if hasattr(user, 'kyc') else 'pending',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_dashboard(request):
    """
    Full dashboard payload for the mobile app.
    Returns profile, stats, last 5 claims, last 5 payouts, zone forecast.
    """
    user = request.user

    try:
        profile = user.workerprofile
    except WorkerProfile.DoesNotExist:
        return Response({'error': 'Profile not found.'}, status=404)

    profile_data = WorkerProfileSerializer(profile).data

    # Recent claims
    claims = []
    try:
        from apps.claims.models import Claim
        for c in Claim.objects.filter(worker=user).order_by('-created_at')[:5]:
            claims.append({
                'id':            c.pk,
                'status':        c.status,
                'payout_amount': float(c.payout_amount),
                'fraud_score':   c.fraud_score,
                'trigger_type':  c.disruption_event.trigger_type if c.disruption_event else None,
                'created_at':    c.created_at,
            })
    except Exception as e:
        logger.warning(f"Could not load claims for dashboard: {e}")

    # Recent payouts
    payouts = []
    try:
        for p in user.payouts.order_by('-initiated_at')[:5]:
            payouts.append({
                'id':          p.pk,
                'amount':      float(p.amount),
                'status':      p.status,
                'utr_number':  p.utr_number,
                'credited_at': p.credited_at,
            })
    except Exception as e:
        logger.warning(f"Could not load payouts for dashboard: {e}")

    # Zone forecast
    forecast = None
    try:
        if profile.zone:
            fc = profile.zone.forecasts.order_by('-generated_at').first()
            if fc:
                forecast = {
                    'forecast_date':      fc.forecast_date,
                    'rain_probability':   float(fc.rain_probability),
                    'heat_probability':   float(fc.heat_probability),
                    'aqi_probability':    float(fc.aqi_probability),
                    'overall_risk_level': fc.overall_risk_level,
                }
    except Exception:
        pass

    return Response({
        'profile':  profile_data,
        'claims':   claims,
        'payouts':  payouts,
        'forecast': forecast,
    })
