"""apps/circles/serializers.py"""
from rest_framework import serializers
from .models import RiskCircle, CircleMembership


class RiskCircleSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    zone_name    = serializers.CharField(source='zone.display_name', read_only=True)
    is_full      = serializers.BooleanField(read_only=True)

    class Meta:
        model  = RiskCircle
        fields = [
            'id', 'name', 'description', 'zone', 'zone_name',
            'pool_balance', 'max_members', 'member_count', 'is_full',
            'is_active', 'created_at',
        ]
        read_only_fields = fields


class CircleMembershipSerializer(serializers.ModelSerializer):
    circle_name  = serializers.CharField(source='circle.name',             read_only=True)
    zone_name    = serializers.CharField(source='circle.zone.display_name', read_only=True)
    pool_balance = serializers.DecimalField(
        source='circle.pool_balance', max_digits=12, decimal_places=2, read_only=True
    )
    member_count = serializers.IntegerField(source='circle.member_count', read_only=True)

    class Meta:
        model  = CircleMembership
        fields = [
            'id', 'circle', 'circle_name', 'zone_name',
            'pool_balance', 'member_count',
            'contribution_total', 'is_active', 'joined_at',
        ]
        read_only_fields = fields
