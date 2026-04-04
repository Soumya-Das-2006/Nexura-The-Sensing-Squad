from rest_framework import serializers
from .models import Zone


class ZoneSerializer(serializers.ModelSerializer):
    risk_level  = serializers.ReadOnlyField()
    risk_color  = serializers.ReadOnlyField()
    display_name = serializers.ReadOnlyField()

    class Meta:
        model  = Zone
        fields = [
            'id', 'city', 'area_name', 'state',
            'lat', 'lng', 'radius_km',
            'risk_multiplier', 'risk_level', 'risk_color',
            'display_name', 'active',
        ]


class ZoneListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdowns."""
    class Meta:
        model  = Zone
        fields = ['id', 'city', 'area_name', 'risk_multiplier']
