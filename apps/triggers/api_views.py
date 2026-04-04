"""
apps/triggers/api_views.py

GET  /api/v1/triggers/recent/          → recent 20 disruption events (worker zone)
GET  /api/v1/triggers/zone/<zone_id>/  → all events for a specific zone
POST /api/v1/triggers/fire/            → manually fire a trigger (admin only, testing)
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .models import DisruptionEvent
from .serializers import DisruptionEventSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_events(request):
    """
    Returns the 20 most recent DisruptionEvents for the worker's zone.
    Falls back to all zones if the worker has no zone set.
    """
    zone = None
    try:
        zone = request.user.workerprofile.zone
    except Exception:
        pass

    qs = DisruptionEvent.objects.select_related('zone').order_by('-started_at')
    if zone:
        qs = qs.filter(zone=zone)

    serializer = DisruptionEventSerializer(qs[:20], many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def zone_events(request, zone_id):
    """All disruption events for a specific zone (last 50)."""
    qs = DisruptionEvent.objects.filter(
        zone_id=zone_id
    ).order_by('-started_at')[:50]
    return Response(DisruptionEventSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def fire_trigger(request):
    """
    Admin-only: manually fire a disruption trigger for testing.
    Body: { zone_id, trigger_type, severity, is_full }
    """
    from .tasks import create_manual_event

    zone_id      = request.data.get('zone_id')
    trigger_type = request.data.get('trigger_type')
    severity     = float(request.data.get('severity', 0))
    is_full      = bool(request.data.get('is_full', True))

    if not zone_id or not trigger_type:
        return Response({'error': 'zone_id and trigger_type are required.'}, status=400)

    result = create_manual_event.delay(zone_id, trigger_type, severity, is_full, 'api_manual')
    return Response({'message': 'Trigger fired.', 'task_id': str(result.id)})
