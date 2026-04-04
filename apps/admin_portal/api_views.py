"""
apps/admin_portal/api_views.py

DRF endpoints for admin operations used by the portal AJAX calls.
All require is_admin=True (IsAdminUser permission).

POST /api/v1/admin/claims/<pk>/approve/   → approve a claim
POST /api/v1/admin/claims/<pk>/reject/    → reject a claim
GET  /api/v1/admin/stats/                 → platform-wide KPI summary
GET  /api/v1/admin/workers/               → paginated worker list (admin)
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_approve_claim(request, claim_id):
    from apps.claims.models import Claim
    from apps.claims.tasks import manually_approve_claim
    try:
        claim = Claim.objects.get(pk=claim_id)
    except Claim.DoesNotExist:
        return Response({'error': 'Claim not found.'}, status=404)
    if claim.status not in ('pending', 'on_hold'):
        return Response({'error': f'Cannot approve claim with status {claim.status}.'}, status=400)
    manually_approve_claim.delay(claim.pk, request.user.pk)
    return Response({'message': f'Claim #{claim_id} approved. Payout queued.'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_reject_claim(request, claim_id):
    from apps.claims.models import Claim
    from apps.claims.tasks import manually_reject_claim
    try:
        claim = Claim.objects.get(pk=claim_id)
    except Claim.DoesNotExist:
        return Response({'error': 'Claim not found.'}, status=404)
    reason = request.data.get('reason', 'Rejected by admin.')
    manually_reject_claim.delay(claim.pk, request.user.pk, reason)
    return Response({'message': f'Claim #{claim_id} rejected.'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):
    from apps.claims.models import Claim
    from apps.payouts.models import Payout
    from apps.policies.models import Policy
    from apps.triggers.models import DisruptionEvent
    from django.contrib.auth import get_user_model
    User = get_user_model()

    now  = timezone.now()
    week = now - timedelta(days=7)

    return Response({
        'total_workers':   User.objects.filter(is_worker=True, is_active=True).count(),
        'active_policies': Policy.objects.filter(status='active').count(),
        'total_paid_out':  float(Payout.objects.filter(status='credited').aggregate(s=Sum('amount'))['s'] or 0),
        'pending_claims':  Claim.objects.filter(status__in=['pending', 'on_hold']).count(),
        'week_triggers':   DisruptionEvent.objects.filter(started_at__gte=week).count(),
        'week_claims':     Claim.objects.filter(created_at__gte=week).count(),
        'week_payouts':    float(Payout.objects.filter(status='credited', credited_at__gte=week).aggregate(s=Sum('amount'))['s'] or 0),
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_workers(request):
    from django.contrib.auth import get_user_model
    from apps.workers.serializers import WorkerProfileSerializer
    User = get_user_model()

    qs = User.objects.filter(is_worker=True).select_related(
        'workerprofile', 'workerprofile__zone'
    ).order_by('-date_joined')[:50]

    data = []
    for worker in qs:
        try:
            data.append(WorkerProfileSerializer(worker.workerprofile).data)
        except Exception:
            pass
    return Response(data)
