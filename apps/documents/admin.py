from django.contrib import admin
from .models import IncomeDNADocument

@admin.register(IncomeDNADocument)
class IncomeDNADocumentAdmin(admin.ModelAdmin):
    list_display  = ('pk', 'worker', 'period_months', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('worker__mobile',)
    readonly_fields = ('created_at', 'updated_at', 'signature_hex')
