from django.contrib import admin
from .models import Zone


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display  = ('city', 'area_name', 'risk_multiplier', 'risk_level_display', 'radius_km', 'active')
    list_filter   = ('city', 'active')
    search_fields = ('area_name', 'city')
    ordering      = ('city', 'area_name')
    list_editable = ('risk_multiplier', 'active')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Location', {
            'fields': ('city', 'area_name', 'state', 'lat', 'lng', 'radius_km')
        }),
        ('Risk', {
            'fields': ('risk_multiplier', 'active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Risk Level')
    def risk_level_display(self, obj):
        return obj.risk_level
