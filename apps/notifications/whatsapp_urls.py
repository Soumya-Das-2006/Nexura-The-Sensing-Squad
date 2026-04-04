# apps/notifications/whatsapp_urls.py
from django.urls import path
from .whatsapp_webhook import WhatsAppWebhookView

urlpatterns = [
    path('webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
]
