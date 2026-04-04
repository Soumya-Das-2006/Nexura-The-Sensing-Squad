"""
apps/payments/api_views.py

GET  /api/v1/payments/          → worker's premium payment history
GET  /api/v1/payments/summary/  → total paid, streak, next payment date
POST /api/v1/payments/webhook/  → Razorpay webhook (no auth)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from .models import PremiumPayment
from .serializers import PremiumPaymentSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_payments(request):
    qs = PremiumPayment.objects.filter(
        worker=request.user
    ).select_related('policy__plan_tier').order_by('-week_start_date')[:52]
    return Response(PremiumPaymentSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_summary(request):
    qs       = PremiumPayment.objects.filter(worker=request.user)
    captured = qs.filter(status__in=['captured', 'grace'])
    total    = float(sum(p.amount for p in captured))

    # Next Monday
    today      = timezone.now().date()
    days_ahead = (7 - today.weekday()) % 7 or 7
    next_monday = today + timedelta(days=days_ahead)

    # Consecutive weeks paid (streak)
    streak = 0
    for payment in qs.filter(status__in=['captured', 'grace']).order_by('-week_start_date'):
        expected = next_monday - timedelta(weeks=streak + 1)
        if payment.week_start_date == expected:
            streak += 1
        else:
            break

    return Response({
        'total_paid':        total,
        'weeks_paid':        captured.count(),
        'payment_streak':    streak,
        'next_payment_date': str(next_monday),
    })
