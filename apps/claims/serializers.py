"""apps/claims/serializers.py"""
from rest_framework import serializers
from .models import Claim


class ClaimSerializer(serializers.ModelSerializer):
    trigger_type    = serializers.CharField(
        source='disruption_event.trigger_type', read_only=True
    )
    trigger_label   = serializers.CharField(
        source='disruption_event.get_trigger_type_display', read_only=True
    )
    zone_name       = serializers.CharField(
        source='disruption_event.zone.display_name', read_only=True
    )
    plan_name       = serializers.CharField(
        source='policy.plan_tier.name', read_only=True
    )
    fraud_tier      = serializers.CharField(read_only=True)
    fraud_color     = serializers.CharField(read_only=True)
    trigger_icon    = serializers.CharField(read_only=True)
    has_payout      = serializers.BooleanField(read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Claim
        fields = [
            'id', 'trigger_type', 'trigger_label', 'zone_name', 'plan_name',
            'payout_amount', 'fraud_score', 'fraud_tier', 'fraud_color',
            'trigger_icon', 'status', 'status_display',
            'rejection_reason', 'has_payout',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
