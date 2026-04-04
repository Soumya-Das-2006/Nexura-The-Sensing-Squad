"""apps/triggers/serializers.py"""
from rest_framework import serializers
from .models import DisruptionEvent


class DisruptionEventSerializer(serializers.ModelSerializer):
    trigger_label    = serializers.CharField(source='get_trigger_type_display', read_only=True)
    zone_name        = serializers.CharField(source='zone.display_name', read_only=True)
    icon             = serializers.CharField(read_only=True)
    color            = serializers.CharField(read_only=True)

    class Meta:
        model  = DisruptionEvent
        fields = [
            'id', 'zone', 'zone_name',
            'trigger_type', 'trigger_label',
            'severity_value', 'threshold_value',
            'is_full_trigger', 'affected_platform',
            'started_at', 'ended_at', 'duration_hours',
            'source_api', 'claims_generated',
            'icon', 'color', 'created_at',
        ]
        read_only_fields = fields
