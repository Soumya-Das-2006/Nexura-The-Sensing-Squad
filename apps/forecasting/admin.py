"""apps/forecasting/admin.py"""
from django.contrib import admin
from django.utils.html import format_html
from .models import ZoneForecast


@admin.register(ZoneForecast)
class ZoneForecastAdmin(admin.ModelAdmin):
    list_display  = (
        'zone', 'forecast_date', 'risk_display',
        'rain_probability', 'heat_probability', 'aqi_probability',
        'disruption_probability', 'generated_at',
    )
    list_filter   = ('overall_risk_level', 'zone__city', 'forecast_date')
    search_fields = ('zone__area_name', 'zone__city')
    readonly_fields = ('generated_at', 'updated_at')
    date_hierarchy  = 'forecast_date'
    ordering        = ('-forecast_date', 'zone__city')
    actions         = ['regenerate_forecasts']

    def risk_display(self, obj):
        colors = {
            'Low':      '#22c55e',
            'Moderate': '#f59e0b',
            'High':     '#ef4444',
            'Critical': '#7c3aed',
        }
        color = colors.get(obj.overall_risk_level, '#6b7280')
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            color, obj.overall_risk_level,
        )
    risk_display.short_description = 'Risk Level'

    @admin.action(description='Regenerate forecasts for selected zones')
    def regenerate_forecasts(self, request, queryset):
        from .tasks import generate_zone_forecasts
        generate_zone_forecasts.delay()
        self.message_user(request, 'Forecast regeneration task queued.')
