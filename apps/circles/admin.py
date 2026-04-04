from django.contrib import admin
from .models import RiskCircle, CircleMembership

@admin.register(RiskCircle)
class RiskCircleAdmin(admin.ModelAdmin):
    list_display  = ('name', 'zone', 'member_count', 'pool_balance', 'max_members', 'is_active')
    list_filter   = ('is_active', 'zone__city')
    search_fields = ('name',)

@admin.register(CircleMembership)
class CircleMembershipAdmin(admin.ModelAdmin):
    list_display  = ('worker', 'circle', 'is_active', 'contribution_total', 'joined_at')
    list_filter   = ('is_active', 'circle')
    search_fields = ('worker__mobile',)
