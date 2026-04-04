"""apps/fraud/serializers.py"""
from rest_framework import serializers
from .models import FraudFlag


class FraudFlagSerializer(serializers.ModelSerializer):
    layer_label = serializers.CharField(source='get_layer_display', read_only=True)
    flag_label  = serializers.CharField(source='get_flag_type_display', read_only=True)

    class Meta:
        model  = FraudFlag
        fields = [
            'id', 'layer', 'layer_label', 'flag_type', 'flag_label',
            'score_contribution', 'detail', 'created_at',
        ]
        read_only_fields = fields
