# apps/notifications/whatsapp_urls.py
#
# WhatsApp webhook URL configuration.
# Supports BOTH:
#   - Existing Meta Cloud API webhook (kept for backward-compat)
#   - NEW Twilio WhatsApp webhook (primary for chatbot)
#
# Mount in nexura/urls.py:
#   path('api/v1/whatsapp/', include('apps.notifications.whatsapp_urls')),

from django.urls import path
from .whatsapp_webhook         import WhatsAppWebhookView          # existing Meta
from .twilio_whatsapp_webhook  import TwilioWhatsAppWebhookView    # NEW Twilio

urlpatterns = [
    # Existing Meta Cloud API webhook (preserved — do not remove)
    path('webhook/',         WhatsAppWebhookView.as_view(),       name='whatsapp_webhook_meta'),

    # NEW: Twilio WhatsApp chatbot webhook
    path('webhook/twilio/',  TwilioWhatsAppWebhookView.as_view(), name='whatsapp_webhook_twilio'),
]
