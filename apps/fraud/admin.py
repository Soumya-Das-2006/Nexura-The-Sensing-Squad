"""apps/fraud/admin.py"""
from django.contrib import admin
from django.utils.html import format_html
from .models import FraudFlag


@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
    list_display  = (
        'pk', 'claim_link', 'layer_display', 'flag_type',
        'score_display', 'detail_short', 'created_at',
    )
    list_filter   = ('layer', 'flag_type')
    search_fields = ('claim__worker__mobile', 'detail')
    readonly_fields = ('created_at',)
    raw_id_fields   = ('claim',)
    ordering        = ('-created_at',)

    def claim_link(self, obj):
        return format_html(
            '<a href="/django-admin/claims/claim/{}/change/">Claim #{}</a>',
            obj.claim_id, obj.claim_id,
        )
    claim_link.short_description = 'Claim'

    def layer_display(self, obj):
        colors = {1: '#6b7280', 2: '#3b82f6', 3: '#8b5cf6',
                  4: '#f59e0b', 5: '#ef4444', 6: '#dc2626'}
        color = colors.get(obj.layer, '#6b7280')
        return format_html(
            '<span style="color:{};font-weight:600;">Layer {}</span>', color, obj.layer
        )
    layer_display.short_description = 'Layer'

    def score_display(self, obj):
        score = obj.score_contribution
        color = '#22c55e' if score < 0.3 else '#f59e0b' if score < 0.6 else '#ef4444'
        return format_html(
            '<span style="color:{};font-weight:600;">{:.3f}</span>', color, score
        )
    score_display.short_description = 'Score Contribution'

    def detail_short(self, obj):
        return obj.detail[:80] + ('…' if len(obj.detail) > 80 else '')
    detail_short.short_description = 'Detail'
