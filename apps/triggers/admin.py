from django.contrib import admin
from django.utils.html import format_html
from .models import DisruptionEvent


@admin.register(DisruptionEvent)
class DisruptionEventAdmin(admin.ModelAdmin):
    list_display  = (
        'trigger_display', 'zone', 'severity_value', 'is_full_trigger',
        'claims_generated', 'started_at', 'ended_at', 'source_api',
    )
    list_filter   = ('trigger_type', 'is_full_trigger', 'claims_generated', 'zone__city')
    search_fields = ('zone__area_name', 'zone__city', 'source_api')
    readonly_fields = ('created_at', 'raw_payload', 'duration_hours')
    date_hierarchy = 'started_at'
    ordering       = ('-started_at',)

    actions = ['close_events', 'trigger_claim_generation']

    def trigger_display(self, obj):
        colors = {
            'heavy_rain':    '#015fc9',
            'extreme_heat':  '#dc2626',
            'severe_aqi':    '#ca8a04',
            'flash_flood':   '#0891b2',
            'curfew_strike': '#64748b',
            'platform_down': '#1e293b',
        }
        icons = {
            'heavy_rain':    '🌧️',
            'extreme_heat':  '🌡️',
            'severe_aqi':    '🌫️',
            'flash_flood':   '🌊',
            'curfew_strike': '🚫',
            'platform_down': '🖥️',
        }
        color = colors.get(obj.trigger_type, '#6b7280')
        icon  = icons.get(obj.trigger_type, '⚡')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color, icon, obj.get_trigger_type_display(),
        )
    trigger_display.short_description = 'Trigger'

    @admin.action(description='Close selected events (mark ended_at = now)')
    def close_events(self, request, queryset):
        for event in queryset.filter(ended_at__isnull=True):
            event.close()
        self.message_user(request, f'Closed {queryset.count()} events.')

    @admin.action(description='Trigger claim generation for selected events')
    def trigger_claim_generation(self, request, queryset):
        from apps.claims.tasks import process_pending_claims
        process_pending_claims.delay()
        queryset.update(claims_generated=False)
        self.message_user(request, 'Claim generation task queued.')
