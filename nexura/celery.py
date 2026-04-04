import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexura.settings.development')

app = Celery('nexura')

# Load config from Django settings — all CELERY_* keys
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')