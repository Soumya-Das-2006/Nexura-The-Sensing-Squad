from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django admin
    path('django-admin/', admin.site.urls),

    # Public web pages
    path('', include('apps.core.urls')),

    # Auth (web)
    path('', include('apps.accounts.urls')),

    # Worker web views
    path('', include('apps.workers.urls')),
    path('', include('apps.policies.urls')),
    path('', include('apps.claims.urls')),
    path('', include('apps.payouts.urls')),
    path('', include('apps.payments.urls')),
    path('', include('apps.forecasting.urls')),
    path('', include('apps.circles.urls')),
    path('', include('apps.documents.urls')),
    path('', include('apps.pricing.urls')),
    path('', include('apps.chatbot.urls')),
    
    # Admin portal web views
    path('', include('apps.admin_portal.urls')),

    # REST API v1
    path('api/v1/auth/',         include('apps.accounts.api_urls')),
    path('api/v1/workers/',      include('apps.workers.api_urls')),
    path('api/v1/zones/',        include('apps.zones.api_urls')),
    path('api/v1/policies/',     include('apps.policies.api_urls')),
    path('api/v1/claims/',       include('apps.claims.api_urls')),
    path('api/v1/payouts/',      include('apps.payouts.api_urls')),
    path('api/v1/payments/',     include('apps.payments.api_urls')),
    path('api/v1/pricing/',      include('apps.pricing.api_urls')),
    path('api/v1/circles/',      include('apps.circles.api_urls')),
    path('api/v1/documents/',    include('apps.documents.api_urls')),
    path('api/v1/admin/',        include('apps.admin_portal.api_urls')),
    path('api/v1/whatsapp/',     include('apps.notifications.whatsapp_urls')),

    # API health check
    path('api/v1/health/', include('apps.core.health_urls')),
    path('health/', include('apps.core.health_urls')),

    # API docs
    path('api/v1/schema/',  SpectacularAPIView.as_view(),     name='schema'),
    path('api/v1/docs/',    SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/',   SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),
]

# Serve media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
