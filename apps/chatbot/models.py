"""
apps/chatbot/models.py

Database models for the Nexura AI Chatbot system.

Models:
    ChatSession     — one conversation session per user
    ChatMessage     — individual messages within a session
    UserLangPref    — persisted language preference per user/phone
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatSession(models.Model):
    """
    Represents a single conversation session.
    A new session is created when a user starts chatting
    (or after 30 minutes of inactivity).
    """

    CHANNEL_WEB       = 'web'
    CHANNEL_WHATSAPP  = 'whatsapp'
    CHANNEL_CHOICES   = [(CHANNEL_WEB, 'Web'), (CHANNEL_WHATSAPP, 'WhatsApp')]

    STATE_IDLE        = 'idle'
    STATE_GREETED     = 'greeted'
    STATE_COLLECTING  = 'collecting'
    STATE_PROCESSING  = 'processing'
    STATE_RESOLVED    = 'resolved'
    STATE_ESCALATED   = 'escalated'
    STATE_CHOICES     = [
        (STATE_IDLE,       'Idle'),
        (STATE_GREETED,    'Greeted'),
        (STATE_COLLECTING, 'Collecting Info'),
        (STATE_PROCESSING, 'Processing'),
        (STATE_RESOLVED,   'Resolved'),
        (STATE_ESCALATED,  'Escalated to Agent'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chat_sessions',
    )
    # For unauthenticated / WhatsApp users
    phone       = models.CharField(max_length=20, blank=True, db_index=True)
    channel     = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_WEB)
    language    = models.CharField(max_length=10, default='en')
    state       = models.CharField(max_length=20, choices=STATE_CHOICES, default=STATE_IDLE)

    # Conversation context stored as JSON (intent history, collected slots)
    context     = models.JSONField(default=dict)

    started_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    ended_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes  = [
            models.Index(fields=['phone', 'channel']),
            models.Index(fields=['user', 'channel']),
        ]

    def __str__(self):
        who = self.user or self.phone or 'anonymous'
        return f"Session({who} | {self.channel} | {self.state})"

    def is_active(self) -> bool:
        if self.ended_at:
            return False
        timeout = timezone.now() - timezone.timedelta(minutes=30)
        return self.updated_at >= timeout

    def end(self):
        self.ended_at = timezone.now()
        self.state    = self.STATE_RESOLVED
        self.save(update_fields=['ended_at', 'state'])


class ChatMessage(models.Model):
    """Individual message within a ChatSession."""

    ROLE_USER      = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_SYSTEM    = 'system'
    ROLE_CHOICES   = [
        (ROLE_USER,      'User'),
        (ROLE_ASSISTANT, 'Assistant'),
        (ROLE_SYSTEM,    'System'),
    ]

    TYPE_TEXT     = 'text'
    TYPE_INTENT   = 'intent_result'   # internal event, not shown to user
    TYPE_ERROR    = 'error'
    TYPE_CHOICES  = [
        (TYPE_TEXT,   'Text'),
        (TYPE_INTENT, 'Intent Result'),
        (TYPE_ERROR,  'Error'),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session     = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role        = models.CharField(max_length=15, choices=ROLE_CHOICES)
    msg_type    = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_TEXT)
    content     = models.TextField()

    # Metadata
    intent      = models.CharField(max_length=60, blank=True)   # detected intent
    language    = models.CharField(max_length=10, blank=True)   # detected language
    confidence  = models.FloatField(default=0.0)                # intent confidence
    llm_used    = models.BooleanField(default=False)            # was LLM called?
    tokens_used = models.IntegerField(default=0)                # LLM tokens consumed
    latency_ms  = models.IntegerField(default=0)                # response time

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class UserLangPref(models.Model):
    """
    Persisted language preference — survives session expiry.
    Keyed on phone (WhatsApp) or user FK (web).
    """
    user        = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='lang_pref',
    )
    phone       = models.CharField(max_length=20, unique=True, blank=True)
    language    = models.CharField(max_length=10, default='en')
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name      = 'User Language Preference'
        verbose_name_plural = 'User Language Preferences'

    def __str__(self):
        who = self.user or self.phone
        return f"LangPref({who} → {self.language})"
