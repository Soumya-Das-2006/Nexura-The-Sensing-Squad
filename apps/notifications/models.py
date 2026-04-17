from django.db import models
from django.conf import settings

class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('mock', 'Mock (Sandbox)'),
    ]

    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    event_type = models.CharField(max_length=50)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='mock')
    error_detail = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.channel.upper()} to {self.mobile or (self.worker.mobile if self.worker else '')} - {self.event_type} ({self.status})"
