"""
apps/fraud/api_views.py

GET  /api/v1/fraud/flags/<claim_pk>/   → fraud flags for a specific claim
GET  /api/v1/fraud/status/             → model load status (admin only)
POST /api/v1/fraud/rescore/<claim_pk>/ → re-score a single claim (admin only)
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import FraudFlag
from .serializers import FraudFlagSerializer
from .loader import models_available, load_models, score_claim

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def claim_flags(request, claim_pk):
    """Return all fraud flags for a specific claim owned by the current worker."""
    flags = FraudFlag.objects.filter(
        claim__pk=claim_pk,
        claim__worker=request.user,
    ).order_by('layer', 'created_at')
    return Response(FraudFlagSerializer(flags, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def model_status(request):
    """Return current fraud model load status — admin only."""
    from .loader import _iso_forest, _xgb_model, _feature_cols
    return Response({
        'models_loaded':    models_available(),
        'iso_forest_ready': _iso_forest is not None,
        'xgb_ready':        _xgb_model is not None,
        'feature_count':    len(_feature_cols) if _feature_cols else 0,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def rescore_claim(request, claim_pk):
    """Re-score a single claim and update its fraud_score — admin only."""
    from apps.claims.models import Claim
    try:
        claim = Claim.objects.get(pk=claim_pk)
    except Claim.DoesNotExist:
        return Response({'error': 'Claim not found.'}, status=404)

    iso_score, xgb_score, combined = score_claim(claim)

    claim.fraud_score = combined
    claim.save(update_fields=['fraud_score', 'updated_at'])

    return Response({
        'claim_id':   claim.pk,
        'iso_score':  iso_score,
        'xgb_score':  xgb_score,
        'combined':   combined,
        'old_status': claim.status,
    })
