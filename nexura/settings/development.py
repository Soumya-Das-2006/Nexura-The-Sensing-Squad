from .base import *

DEBUG = True

# Show emails in console during dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar (optional — install separately if needed)
INTERNAL_IPS = ['127.0.0.1']

# Relaxed CORS for local development
CORS_ALLOW_ALL_ORIGINS = True

# Logging to console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'apps':   {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'celery': {'handlers': ['console'], 'level': 'INFO'},
    },
}
# Allow Django test client host
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver', '*']
