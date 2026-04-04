"""
apps/workers/serializers.py
"""
from rest_framework import serializers
from .models import WorkerProfile


class WorkerProfileSerializer(serializers.ModelSerializer):
    mobile       = serializers.CharField(source='user.mobile', read_only=True)
    city         = serializers.CharField(read_only=True)
    risk_label   = serializers.CharField(read_only=True)
    risk_color   = serializers.CharField(read_only=True)
    kyc_status   = serializers.SerializerMethodField()
    platform_display = serializers.CharField(
        source='get_platform_display', read_only=True
    )
    zone_name    = serializers.CharField(
        source='zone.display_name', read_only=True
    )

    class Meta:
        model  = WorkerProfile
        fields = [
            'id', 'mobile', 'name', 'platform', 'platform_display',
            'segment', 'zone', 'zone_name', 'city',
            'upi_id', 'risk_score', 'risk_label', 'risk_color',
            'razorpay_ready', 'kyc_status',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'mobile', 'city', 'risk_score', 'risk_label', 'risk_color',
            'razorpay_ready', 'kyc_status', 'created_at', 'updated_at',
        ]

    def get_kyc_status(self, obj):
        return obj.kyc_status()


class WorkerProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /api/v1/workers/profile/"""
    class Meta:
        model  = WorkerProfile
        fields = ['name', 'platform', 'segment', 'zone', 'upi_id']
