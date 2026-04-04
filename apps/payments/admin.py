from django.contrib import admin
from django.utils.html import format_html
from .models import PremiumPayment


@admin.register(PremiumPayment)
class PremiumPaymentAdmin(admin.ModelAdmin):
    list_display  = (
        'pk', 'worker_mobile', 'plan_name', 'amount_display',
        'week_start_date', 'status_display', 'razorpay_payment_id',
        'created_at',
    )
    list_filter   = ('status', 'policy__plan_tier')
    search_fields = ('worker__mobile', 'razorpay_payment_id', 'razorpay_subscription_id')
    readonly_fields = (
        'created_at', 'updated_at',
        'razorpay_payment_id', 'razorpay_order_id',
        'razorpay_subscription_id', 'razorpay_signature',
    )
    raw_id_fields  = ('policy', 'worker')
    date_hierarchy = 'week_start_date'
    ordering       = ('-week_start_date',)
    actions        = ['mark_captured', 'mark_failed']

    def worker_mobile(self, obj):
        return obj.worker.mobile
    worker_mobile.short_description = 'Worker'

    def plan_name(self, obj):
        return obj.policy.plan_tier.name
    plan_name.short_description = 'Plan'

    def amount_display(self, obj):
        return format_html('<strong>₹{}</strong>', int(obj.amount))
    amount_display.short_description = 'Amount'

    def status_display(self, obj):
        colors = {
            'captured': '#22c55e',
            'pending':  '#f59e0b',
            'failed':   '#ef4444',
            'grace':    '#8b5cf6',
            'refunded': '#6b7280',
        }
        icons = {
            'captured': '✓', 'pending': '⏳',
            'failed': '✗', 'grace': '🎁', 'refunded': '↩',
        }
        color = colors.get(obj.status, '#6b7280')
        icon  = icons.get(obj.status, '')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color, icon, obj.get_status_display(),
        )
    status_display.short_description = 'Status'

    @admin.action(description='Mark selected payments as Captured (sandbox fix)')
    def mark_captured(self, request, queryset):
        import uuid
        for p in queryset.filter(status='pending'):
            p.capture(razorpay_payment_id=f"pay_{uuid.uuid4().hex[:14]}")
        self.message_user(request, f'Captured {queryset.count()} payments.')

    @admin.action(description='Mark selected payments as Failed')
    def mark_failed(self, request, queryset):
        for p in queryset.filter(status='pending'):
            p.fail('Marked failed by admin.')
        self.message_user(request, f'Failed {queryset.count()} payments.')
