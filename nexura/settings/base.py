"""
Nexura — Base Settings
Shared across all environments.
"""
import os
from pathlib import Path
import environ

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Environment ──────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    OTP_TEST_MODE=(bool, True),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# ─── Security ─────────────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY', default='django-insecure-nexura-default-key-change-me')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '0.0.0.0'])

# ─── Application Definition ───────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.workers',
    'apps.zones',
    'apps.policies',
    'apps.triggers',
    'apps.claims',
    'apps.payouts',
    'apps.payments',
    'apps.fraud',
    'apps.pricing',
    'apps.forecasting',
    'apps.notifications',
    'apps.circles',
    'apps.documents',
    'apps.admin_portal',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nexura.urls'
AUTH_USER_MODEL = 'accounts.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
WSGI_APPLICATION = 'nexura.wsgi.application'

# ─── Templates ────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Nexura global context
                'apps.core.context_processors.nexura_globals',
            ],
        },
    },
]

# ─── Database — SQLite by default, PostgreSQL if DB_NAME set ──────────────────
_db_name = env('DB_NAME', default='')
if _db_name:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _db_name,
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─── Cache — Redis if available, else LocMem fallback ─────────────────────────
_redis_url = env('REDIS_URL', default='')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ─── Static & Media ───────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Use simple storage in dev (no manifest needed), CompressedManifest in prod
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Authentication ───────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ─── REST Framework ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─── JWT ──────────────────────────────────────────────────────────────────────
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'AUTH_HEADER_TYPES':      ('Bearer',),
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

# ─── Celery ───────────────────────────────────────────────────────────────────
CELERY_BROKER_URL         = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND     = env('CELERY_RESULT_BACKEND', default='django-db')
CELERY_ACCEPT_CONTENT     = ['json']
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
CELERY_TIMEZONE           = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER     = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_ALWAYS_EAGER  = False

# ─── Celery Production Hardening ──────────────────────────────────
CELERY_TASK_ACKS_LATE               = True     # ACK after execution — re-deliver on crash
CELERY_WORKER_PREFETCH_MULTIPLIER   = 1        # Don't hoard tasks — fair distribution
CELERY_TASK_REJECT_ON_WORKER_LOST   = True     # Re-queue if worker is killed
CELERY_TASK_SOFT_TIME_LIMIT         = 120      # Raise SoftTimeLimitExceeded after 2 min
CELERY_TASK_TIME_LIMIT              = 180      # Hard kill after 3 min
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True  # Retry Redis connection on startup
CELERY_WORKER_MAX_TASKS_PER_CHILD   = 1000     # Restart worker after 1000 tasks (memory leak guard)
CELERY_TASK_TRACK_STARTED           = True     # Track STARTED state in result backend
CELERY_WORKER_SEND_TASK_EVENTS      = True     # Enable task monitoring events

# ─── Celery Beat Schedule ─────────────────────────────────────────────────────
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'poll-weather-all-zones': {
        'task': 'apps.triggers.tasks.poll_weather_all_zones',
        'schedule': crontab(minute='*/15'),
    },
    'poll-aqi-all-zones': {
        'task': 'apps.triggers.tasks.poll_aqi_all_zones',
        'schedule': crontab(minute='*/30'),
    },
    'poll-platform-uptime': {
        'task': 'apps.triggers.tasks.poll_platform_uptime',
        'schedule': crontab(minute='*/10'),
    },
    'process-pending-claims': {
        'task': 'apps.claims.tasks.process_pending_claims',
        'schedule': crontab(minute='*/5'),
    },
    'daily-fraud-batch-scan': {
        'task': 'apps.fraud.tasks.daily_batch_fraud_scan',
        'schedule': crontab(hour=2, minute=0),
    },
    'weekly-premium-collection': {
        'task': 'apps.payments.tasks.collect_weekly_premiums',
        'schedule': crontab(day_of_week='monday', hour=0, minute=1),
    },
    'weekly-premium-recalculation': {
        'task': 'apps.pricing.tasks.recalculate_all_premiums',
        'schedule': crontab(day_of_week='sunday', hour=20, minute=0),
    },
    'weekly-zone-forecasts': {
        'task': 'apps.forecasting.tasks.generate_zone_forecasts',
        'schedule': crontab(day_of_week='sunday', hour=20, minute=30),
    },
    # Fixed: was pointing to notifications.tasks but function is in forecasting.tasks
    'weekly-forecast-alerts': {
        'task': 'apps.forecasting.tasks.send_forecast_alerts',
        'schedule': crontab(day_of_week='sunday', hour=21, minute=0),
    },
}

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

# ─── API Docs ─────────────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Nexura API',
    'DESCRIPTION': "AI-Powered Parametric Income Protection for India's Gig Workers",
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ─── External Services ────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = env('OPENWEATHER_API_KEY', default='')
WAQI_API_KEY        = env('WAQI_API_KEY', default='')

RAZORPAY_KEY_ID            = env('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET        = env('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_WEBHOOK_SECRET    = env('RAZORPAY_WEBHOOK_SECRET', default='')
RAZORPAY_ACCOUNT_NUMBER    = env('RAZORPAY_ACCOUNT_NUMBER', default='')
RAZORPAY_WEEKLY_PLAN_ID    = env('RAZORPAY_WEEKLY_PLAN_ID', default='')

WHATSAPP_TOKEN        = env('WHATSAPP_TOKEN', default='')
WHATSAPP_PHONE_ID     = env('WHATSAPP_PHONE_ID', default='')
WHATSAPP_VERIFY_TOKEN = env('WHATSAPP_VERIFY_TOKEN', default='nexura_verify')

TWILIO_ACCOUNT_SID  = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN   = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', default='')

SENDGRID_API_KEY   = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@nexaura.in')

AWS_ACCESS_KEY_ID       = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY   = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='nexaura-documents')
AWS_S3_REGION_NAME      = env('AWS_S3_REGION_NAME', default='ap-south-1')

OTP_EXPIRY_MINUTES = env.int('OTP_EXPIRY_MINUTES', default=10)
OTP_TEST_MODE      = env.bool('OTP_TEST_MODE', default=True)
OTP_TEST_CODE      = env('OTP_TEST_CODE', default='123456')

# ML Models path
ML_MODELS_DIR = BASE_DIR / 'ml_models'

FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')
