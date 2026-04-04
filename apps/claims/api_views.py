"""
apps/claims/api_views.py

GET  /api/v1/claims/         → list worker's claims (filterable by status)
GET  /api/v1/claims/<pk>/    → single claim detail with fraud flags
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Claim
from .serializers import ClaimSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_claims(request):
    qs = Claim.objects.filter(
        worker=request.user
    ).select_related(
        'disruption_event', 'disruption_event__zone', 'policy__plan_tier'
    ).order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    return Response(ClaimSerializer(qs[:50], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def claim_detail_api(request, pk):
    try:
        claim = Claim.objects.select_related(
            'disruption_event', 'disruption_event__zone',
            'policy__plan_tier'
        ).get(pk=pk, worker=request.user)
    except Claim.DoesNotExist:
        return Response({'error': 'Claim not found.'}, status=404)

    data = ClaimSerializer(claim).data
    data['fraud_flags'] = claim.fraud_flags  # full pipeline audit trail
    return Response(data)
