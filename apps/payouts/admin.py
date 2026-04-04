from django.contrib import admin
from django.utils.html import format_html
from .models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display  = (
        'pk', 'worker_mobile', 'amount_display', 'mode',
        'status_display', 'utr_number', 'retry_count',
        'initiated_at', 'credited_at',
    )
    list_filter   = ('status', 'mode')
    search_fields = ('worker__mobile', 'utr_number', 'razorpay_payout_id')
    readonly_fields = (
        'created_at', 'updated_at', 'razorpay_payout_id',
        'razorpay_fund_acct_id', 'time_to_credit',
    )
    raw_id_fields  = ('claim', 'worker')
    date_hierarchy = 'initiated_at'
    ordering       = ('-initiated_at',)
    actions        = ['retry_payouts', 'reconcile_now']

    def worker_mobile(self, obj):
        return obj.worker.mobile
    worker_mobile.short_description = 'Worker'

    def amount_display(self, obj):
        return format_html('<strong>₹{}</strong>', int(obj.amount))
    amount_display.short_description = 'Amount'

    def status_display(self, obj):
        colors = {
            'credited':   '#22c55e',
            'pending':    '#f59e0b',
            'queued':     '#3b82f6',
            'processing': '#8b5cf6',
            'failed':     '#ef4444',
            'reversed':   '#6b7280',
        }
        icons = {
            'credited':   '✓',
            'pending':    '⏳',
            'queued':     '→',
            'processing': '⚙',
            'failed':     '✗',
            'reversed':   '↩',
        }
        color = colors.get(obj.status, '#6b7280')
        icon  = icons.get(obj.status, '')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            color, icon, obj.get_status_display(),
        )
    status_display.short_description = 'Status'

    @admin.action(description='Retry selected failed payouts')
    def retry_payouts(self, request, queryset):
        from .tasks import disburse_payout
        count = 0
        for payout in queryset.filter(status='failed'):
            payout.status = 'pending'
            payout.save(update_fields=['status'])
            disburse_payout.delay(payout.claim_id)
            count += 1
        self.message_user(request, f'Retried {count} payouts.')

    @admin.action(description='Reconcile selected payouts with Razorpay now')
    def reconcile_now(self, request, queryset):
        from .tasks import reconcile_payouts
        reconcile_payouts.delay()
        self.message_user(request, 'Reconciliation task queued.')
