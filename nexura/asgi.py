"""
ASGI config for nexura project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexura.settings.development')
application = get_asgi_application()
