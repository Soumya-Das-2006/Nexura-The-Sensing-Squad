"""
apps/payouts/api_views.py

GET  /api/v1/payouts/          → list worker's payouts
GET  /api/v1/payouts/<pk>/     → single payout detail
GET  /api/v1/payouts/summary/  → totals for the mobile dashboard
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Payout
from .serializers import PayoutSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_payouts(request):
    qs = Payout.objects.filter(
        worker=request.user
    ).select_related(
        'claim__disruption_event', 'claim__disruption_event__zone'
    ).order_by('-initiated_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    return Response(PayoutSerializer(qs[:50], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payout_detail_api(request, pk):
    try:
        payout = Payout.objects.select_related(
            'claim__disruption_event', 'claim__disruption_event__zone'
        ).get(pk=pk, worker=request.user)
    except Payout.DoesNotExist:
        return Response({'error': 'Payout not found.'}, status=404)
    return Response(PayoutSerializer(payout).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payout_summary(request):
    """Aggregate totals for the mobile dashboard."""
    qs = Payout.objects.filter(worker=request.user)
    credited = qs.filter(status='credited')
    return Response({
        'total_credited':     float(sum(p.amount for p in credited)),
        'count_credited':     credited.count(),
        'count_pending':      qs.filter(status__in=['pending', 'queued', 'processing']).count(),
        'count_failed':       qs.filter(status='failed').count(),
        'last_payout_amount': float(credited.order_by('-credited_at').first().amount)
                              if credited.exists() else None,
    })
