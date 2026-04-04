"""apps/forecasting/serializers.py"""
from rest_framework import serializers
from .models import ZoneForecast


class ZoneForecastSerializer(serializers.ModelSerializer):
    zone_name  = serializers.CharField(source='zone.display_name', read_only=True)
    city       = serializers.CharField(source='zone.city',         read_only=True)
    risk_color = serializers.CharField(read_only=True)
    risk_icon  = serializers.CharField(read_only=True)

    class Meta:
        model  = ZoneForecast
        fields = [
            'id', 'zone', 'zone_name', 'city', 'forecast_date',
            'rain_probability', 'heat_probability', 'aqi_probability',
            'disruption_probability', 'overall_risk_level',
            'forecasted_rain_mm', 'forecasted_temp_c', 'forecasted_aqi',
            'risk_color', 'risk_icon', 'generated_at',
        ]
        read_only_fields = fields
