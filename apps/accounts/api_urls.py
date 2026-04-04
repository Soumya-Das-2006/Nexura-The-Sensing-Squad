from django.urls import path
from . import api_views

urlpatterns = [
    path('send-otp/',     api_views.send_otp,        name='api_send_otp'),
    path('verify-otp/',   api_views.verify_otp_api,  name='api_verify_otp'),
    path('refresh/',      api_views.token_refresh,   name='api_token_refresh'),
    path('me/',           api_views.me,               name='api_me'),
    path('logout/',       api_views.logout_api,       name='api_logout'),
]
