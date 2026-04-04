from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display  = (
        'pk', 'worker_mobile', 'trigger_display', 'zone',
        'payout_amount', 'fraud_score_display', 'status_display',
        'created_at',
    )
    list_filter   = ('status', 'disruption_event__trigger_type', 'disruption_event__zone__city')
    search_fields = ('worker__mobile', 'disruption_event__zone__area_name')
    readonly_fields = (
        'created_at', 'updated_at', 'fraud_score', 'fraud_flags',
        'reviewed_by', 'reviewed_at',
    )
    raw_id_fields  = ('worker', 'policy', 'disruption_event', 'reviewed_by')
    date_hierarchy = 'created_at'
    ordering       = ('-created_at',)
    actions        = ['approve_claims', 'reject_claims']

    def worker_mobile(self, obj):
        return obj.worker.mobile
    worker_mobile.short_description = 'Worker'

    def trigger_display(self, obj):
        icons = {
            'heavy_rain': '🌧️', 'extreme_heat': '🌡️', 'severe_aqi': '🌫️',
            'flash_flood': '🌊', 'curfew_strike': '🚫', 'platform_down': '🖥️',
        }
        t = obj.disruption_event.trigger_type if obj.disruption_event else ''
        return format_html('{} {}', icons.get(t, '⚡'), obj.disruption_event.get_trigger_type_display() if obj.disruption_event else '—')
    trigger_display.short_description = 'Trigger'

    def zone(self, obj):
        return obj.disruption_event.zone if obj.disruption_event else '—'
    zone.short_description = 'Zone'

    def fraud_score_display(self, obj):
        score = obj.fraud_score
        color = '#22c55e' if score < 0.5 else '#f59e0b' if score < 0.7 else '#ef4444'
        return format_html(
            '<span style="color:{};font-weight:600;">{:.3f}</span>',
            color, score,
        )
    fraud_score_display.short_description = 'Fraud Score'

    def status_display(self, obj):
        colors = {
            'approved': '#22c55e', 'pending': '#f59e0b',
            'rejected': '#ef4444', 'on_hold': '#8b5cf6',
        }
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display(),
        )
    status_display.short_description = 'Status'

    @admin.action(description='Approve selected claims and queue payout')
    def approve_claims(self, request, queryset):
        count = 0
        for claim in queryset.filter(status__in=['pending', 'on_hold']):
            claim.approve(reviewed_by=request.user)
            from apps.payouts.tasks import disburse_payout
            disburse_payout.delay(claim.pk)
            count += 1
        self.message_user(request, f'Approved {count} claims. Payouts queued.')

    @admin.action(description='Reject selected claims')
    def reject_claims(self, request, queryset):
        count = 0
        for claim in queryset.filter(status__in=['pending', 'on_hold']):
            claim.reject('Rejected via admin bulk action.', reviewed_by=request.user)
            count += 1
        self.message_user(request, f'Rejected {count} claims.')
