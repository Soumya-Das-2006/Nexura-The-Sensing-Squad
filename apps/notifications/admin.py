"""
apps/notifications/admin.py

No models in this app.
Provides an admin action to send a test WhatsApp to a worker.
"""
from django.contrib import admin
from django.contrib import messages as django_messages


def send_test_whatsapp(modeladmin, request, queryset):
    """
    Admin action: send a test WhatsApp message to selected workers.
    Available on WorkerProfile admin.
    """
    from .channels import whatsapp

    count = 0
    for profile in queryset.select_related('user'):
        ok = whatsapp.send_text(
            profile.user.mobile,
            "👋 This is a test message from *Nexura*. "
            "Your notifications are working correctly. 🎉"
        )
        if ok:
            count += 1

    django_messages.success(request, f'Test WhatsApp sent to {count} worker(s).')


send_test_whatsapp.short_description = 'Send test WhatsApp message'


def ready():
    """Inject admin action into WorkerProfileAdmin on app ready."""
    try:
        from apps.workers.admin import WorkerProfileAdmin
        actions = list(WorkerProfileAdmin.actions or [])
        if send_test_whatsapp not in actions:
            actions.append(send_test_whatsapp)
            WorkerProfileAdmin.actions = actions
    except Exception:
        pass
