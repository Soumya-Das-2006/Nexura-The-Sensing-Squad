from django.contrib import admin
from .models import WorkerProfile


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'user', 'platform', 'segment', 'city',
        'risk_score', 'upi_id', 'razorpay_ready', 'created_at',
    )
    list_filter   = ('platform', 'segment', 'zone__city')
    search_fields = ('name', 'user__mobile', 'upi_id')
    readonly_fields = (
        'created_at', 'updated_at', 'risk_updated_at',
        'razorpay_contact_id', 'razorpay_fund_acct_id', 'razorpay_mandate_id',
    )
    raw_id_fields = ('user', 'zone')

    fieldsets = (
        ('Identity',  {'fields': ('user', 'name', 'platform', 'segment', 'zone')}),
        ('Payment',   {'fields': ('upi_id', 'razorpay_contact_id', 'razorpay_fund_acct_id', 'razorpay_mandate_id')}),
        ('Risk',      {'fields': ('risk_score', 'risk_updated_at')}),
        ('Meta',      {'fields': ('grace_tokens', 'created_at', 'updated_at')}),
    )
