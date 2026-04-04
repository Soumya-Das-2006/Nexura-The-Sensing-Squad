"""apps/payments/serializers.py"""
from rest_framework import serializers
from .models import PremiumPayment


class PremiumPaymentSerializer(serializers.ModelSerializer):
    plan_name    = serializers.CharField(source='policy.plan_tier.name', read_only=True)
    week_label   = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = PremiumPayment
        fields = [
            'id', 'plan_name', 'amount', 'week_start_date', 'week_label',
            'status', 'status_display', 'failure_reason',
            'razorpay_payment_id', 'created_at',
        ]
        read_only_fields = fields
