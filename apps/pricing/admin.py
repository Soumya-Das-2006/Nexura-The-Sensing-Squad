"""
apps/pricing/admin.py

No models to register in this app.
Provides admin actions on WorkerProfile for on-demand repricing.
"""
from django.contrib import admin
from django.contrib import messages


# Monkey-patch an admin action onto WorkerProfileAdmin
def recalculate_selected_premiums(modeladmin, request, queryset):
    from apps.pricing.tasks import recalculate_single_worker
    count = 0
    for profile in queryset.select_related('user'):
        recalculate_single_worker.delay(profile.user_id)
        count += 1
    messages.success(request, f'Recalculation queued for {count} worker(s).')


recalculate_selected_premiums.short_description = 'Recalculate XGBoost risk & premium'


# Register the action on WorkerProfileAdmin when apps are ready
def ready():
    try:
        from apps.workers.admin import WorkerProfileAdmin
        WorkerProfileAdmin.actions = list(WorkerProfileAdmin.actions or []) + [
            recalculate_selected_premiums
        ]
    except Exception:
        pass
