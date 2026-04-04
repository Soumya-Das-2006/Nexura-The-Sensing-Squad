"""
apps/circles/api_views.py

GET  /api/v1/circles/my/           → current worker's membership
GET  /api/v1/circles/available/    → circles available in worker's zone
POST /api/v1/circles/<id>/join/    → join a circle
POST /api/v1/circles/<id>/leave/   → leave a circle
GET  /api/v1/circles/              → all active circles (admin)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from .models import RiskCircle, CircleMembership
from .serializers import RiskCircleSerializer, CircleMembershipSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_membership(request):
    """Current worker's active circle membership."""
    membership = CircleMembership.objects.filter(
        worker=request.user, is_active=True
    ).select_related('circle', 'circle__zone').first()

    if not membership:
        return Response({'detail': 'Not a member of any circle.'}, status=404)

    return Response(CircleMembershipSerializer(membership).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_circles(request):
    """Circles available in the worker's zone."""
    try:
        zone = request.user.workerprofile.zone
    except Exception:
        return Response({'error': 'Zone not set.'}, status=400)

    circles = RiskCircle.objects.filter(zone=zone, is_active=True)
    return Response(RiskCircleSerializer(circles, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_circle(request, circle_id):
    """Join a circle."""
    try:
        circle = RiskCircle.objects.get(pk=circle_id, is_active=True)
    except RiskCircle.DoesNotExist:
        return Response({'error': 'Circle not found.'}, status=404)

    if circle.is_full:
        return Response({'error': 'This circle is full.'}, status=400)

    CircleMembership.objects.filter(
        worker=request.user, is_active=True
    ).update(is_active=False)

    membership, created = CircleMembership.objects.update_or_create(
        worker=request.user, circle=circle,
        defaults={'is_active': True},
    )
    return Response({
        'message':  f'Joined {circle.name}.' if created else f'Rejoined {circle.name}.',
        'membership': CircleMembershipSerializer(membership).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_circle(request, circle_id):
    """Leave a circle."""
    updated = CircleMembership.objects.filter(
        worker=request.user, circle_id=circle_id, is_active=True
    ).update(is_active=False)

    if not updated:
        return Response({'error': 'Not a member of this circle.'}, status=400)
    return Response({'message': 'Left the circle successfully.'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def all_circles(request):
    """All circles — admin view."""
    circles = RiskCircle.objects.filter(is_active=True).select_related('zone')
    return Response(RiskCircleSerializer(circles, many=True).data)
