"""
apps/chatbot/migrations/0001_initial.py
"""
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone',      models.CharField(blank=True, db_index=True, max_length=20)),
                ('channel',    models.CharField(choices=[('web', 'Web'), ('whatsapp', 'WhatsApp')], default='web', max_length=20)),
                ('language',   models.CharField(default='en', max_length=10)),
                ('state',      models.CharField(choices=[('idle', 'Idle'), ('greeted', 'Greeted'), ('collecting', 'Collecting Info'), ('processing', 'Processing'), ('resolved', 'Resolved'), ('escalated', 'Escalated to Agent')], default='idle', max_length=20)),
                ('context',    models.JSONField(default=dict)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ended_at',   models.DateTimeField(blank=True, null=True)),
                ('user',       models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role',        models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')], max_length=15)),
                ('msg_type',    models.CharField(choices=[('text', 'Text'), ('intent_result', 'Intent Result'), ('error', 'Error')], default='text', max_length=20)),
                ('content',     models.TextField()),
                ('intent',      models.CharField(blank=True, max_length=60)),
                ('language',    models.CharField(blank=True, max_length=10)),
                ('confidence',  models.FloatField(default=0.0)),
                ('llm_used',    models.BooleanField(default=False)),
                ('tokens_used', models.IntegerField(default=0)),
                ('latency_ms',  models.IntegerField(default=0)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('session',     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chatbot.chatsession')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='UserLangPref',
            fields=[
                ('id',         models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone',      models.CharField(blank=True, max_length=20, unique=True)),
                ('language',   models.CharField(default='en', max_length=10)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user',       models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lang_pref', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='chatsession',
            index=models.Index(fields=['phone', 'channel'], name='chatbot_cha_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='chatsession',
            index=models.Index(fields=['user', 'channel'], name='chatbot_cha_user_idx'),
        ),
    ]
