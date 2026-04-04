from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPRecord, KYCRecord


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('mobile', 'email', 'is_worker', 'mobile_verified', 'profile_complete', 'is_active', 'date_joined')
    list_filter   = ('is_worker', 'is_admin', 'is_active', 'mobile_verified', 'profile_complete')
    search_fields = ('mobile', 'email')
    ordering      = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None,         {'fields': ('mobile', 'email', 'password')}),
        ('Status',     {'fields': ('is_active', 'mobile_verified', 'profile_complete', 'language')}),
        ('Roles',      {'fields': ('is_worker', 'is_admin', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('mobile', 'password1', 'password2', 'is_worker', 'is_admin')}),
    )


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display  = ('mobile', 'purpose', 'created_at', 'expires_at', 'verified', 'attempts')
    list_filter   = ('purpose', 'verified')
    search_fields = ('mobile',)
    readonly_fields = ('created_at',)
    ordering      = ('-created_at',)


@admin.register(KYCRecord)
class KYCRecordAdmin(admin.ModelAdmin):
    list_display  = ('worker', 'status', 'submitted_at', 'verified_at')
    list_filter   = ('status',)
    search_fields = ('worker__mobile',)
    readonly_fields = ('created_at', 'updated_at')
