# apps/chatbot/urls.py
from django.urls import path
from .views import ChatMessageView, ChatHistoryView, EndSessionView, ChatWidgetView

app_name = 'chatbot'

urlpatterns = [
    # Widget page
    path('chatbot/', ChatWidgetView.as_view(), name='widget'),

    # REST API
    path('api/v1/chatbot/message/',      ChatMessageView.as_view(),  name='message'),
    path('api/v1/chatbot/history/',      ChatHistoryView.as_view(),  name='history'),
    path('api/v1/chatbot/session/end/',  EndSessionView.as_view(),   name='end_session'),
]
