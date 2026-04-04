"""apps/payouts/serializers.py"""
from rest_framework import serializers
from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    trigger_type  = serializers.CharField(
        source='claim.disruption_event.trigger_type', read_only=True
    )
    trigger_label = serializers.CharField(
        source='claim.disruption_event.get_trigger_type_display', read_only=True
    )
    zone_name     = serializers.CharField(
        source='claim.disruption_event.zone.display_name', read_only=True
    )
    time_to_credit = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Payout
        fields = [
            'id', 'claim_id', 'trigger_type', 'trigger_label', 'zone_name',
            'amount', 'mode', 'utr_number',
            'status', 'status_display', 'failure_reason',
            'time_to_credit', 'initiated_at', 'credited_at',
            'retry_count',
        ]
        read_only_fields = fields
