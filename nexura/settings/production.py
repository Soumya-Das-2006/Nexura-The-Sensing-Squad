from .base import *
import os

DEBUG = False

# Security
SECURE_HSTS_SECONDS           = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT            = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True

# Logging to file
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} — {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'nexura.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['file', 'console'], 'level': 'WARNING'},
        'apps':   {'handlers': ['file', 'console'], 'level': 'INFO', 'propagate': False},
        'celery': {'handlers': ['file', 'console'], 'level': 'INFO'},
    },
}
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
