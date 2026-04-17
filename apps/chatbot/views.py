"""
apps/chatbot/views.py

REST API views for the Nexura AI Chatbot.

Endpoints:
    POST /api/v1/chatbot/message/      — send a message, get reply
    GET  /api/v1/chatbot/history/      — get session message history
    POST /api/v1/chatbot/session/end/  — end current session
    GET  /api/v1/chatbot/widget/       — serve the chat widget HTML
"""

import logging
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render

from .engine import process_chat_message
from .models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ChatMessageView(View):
    """
    POST /api/v1/chatbot/message/
    Body (JSON): { "message": str, "session_id": str (optional) }
    """

    def post(self, request):
        import json
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        raw_message = (body.get('message') or '').strip()
        session_id  = body.get('session_id')

        if not raw_message:
            return JsonResponse({'error': 'message is required'}, status=400)
        if len(raw_message) > 2000:
            return JsonResponse({'error': 'message too long'}, status=400)

        # Get authenticated user (if any)
        user = request.user if request.user.is_authenticated else None

        try:
            result = process_chat_message(
                raw_message = raw_message,
                session_id  = session_id,
                user        = user,
                channel     = 'web',
            )
            return JsonResponse({
                'session_id': result['session_id'],
                'response':   result['response'],
                'intent':     result['intent'],
                'lang':       result['lang'],
                'state':      result['state'],
                'meta': {
                    'llm_used':   result['llm_used'],
                    'latency_ms': result['latency_ms'],
                },
            })
        except Exception as exc:
            logger.error("[ChatView] Error: %s", exc, exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ChatHistoryView(View):
    """
    GET /api/v1/chatbot/history/?session_id=<uuid>
    Returns last 50 messages for the session.
    """

    def get(self, request):
        session_id = request.GET.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'session_id required'}, status=400)

        try:
            session  = ChatSession.objects.get(pk=session_id)
            messages = ChatMessage.objects.filter(
                session=session,
                msg_type='text',
                role__in=['user', 'assistant'],
            ).order_by('created_at')[:50]

            return JsonResponse({
                'session_id': str(session.pk),
                'language':   session.language,
                'state':      session.state,
                'messages': [
                    {
                        'id':         str(m.pk),
                        'role':       m.role,
                        'content':    m.content,
                        'intent':     m.intent,
                        'created_at': m.created_at.isoformat(),
                    }
                    for m in messages
                ],
            })
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        except Exception as exc:
            logger.error("[HistoryView] Error: %s", exc, exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class EndSessionView(View):
    """POST /api/v1/chatbot/session/end/"""

    def post(self, request):
        import json
        try:
            body       = json.loads(request.body)
            session_id = body.get('session_id')
            session    = ChatSession.objects.get(pk=session_id)
            session.end()
            return JsonResponse({'status': 'ended', 'session_id': session_id})
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        except Exception as exc:
            logger.error("[EndSessionView] %s", exc)
            return JsonResponse({'error': 'Internal server error'}, status=500)


class ChatWidgetView(View):
    """GET /chatbot/ — serves the embedded chat widget page"""

    def get(self, request):
        return render(request, 'chatbot/widget.html')
