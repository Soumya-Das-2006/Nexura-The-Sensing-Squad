"""
apps/notifications/whatsapp_webhook.py

Meta WhatsApp Business Cloud API webhook.

GET  /api/v1/whatsapp/webhook/  → verification challenge
POST /api/v1/whatsapp/webhook/  → incoming message events
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):

    def get(self, request):
        """Handle Meta's webhook verification challenge."""
        mode      = request.GET.get('hub.mode')
        token     = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("[WhatsApp webhook] Verification successful.")
            return HttpResponse(challenge, content_type='text/plain')

        logger.warning("[WhatsApp webhook] Verification failed — bad token.")
        return HttpResponse('Forbidden', status=403)

    def post(self, request):
        """Receive and queue incoming message events."""
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Queue async processing
        from .tasks import process_whatsapp_webhook
        process_whatsapp_webhook.delay(payload)

        # Always return 200 quickly — Meta retries on non-2xx
        return HttpResponse('EVENT_RECEIVED', status=200)
