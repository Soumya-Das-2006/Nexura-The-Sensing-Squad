from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Registration (3 steps) ──────────────────────────────
    path('register/',           views.register_step1_mobile, name='register'),
    path('register/otp/',       views.register_step2_otp,    name='register_otp'),
    path('register/profile/',   views.register_step3_profile, name='register_profile'),
    path('resend-otp/',         views.resend_otp,            name='resend_otp'),

    # ── Login / Logout ──────────────────────────────────────
    path('login/',              views.login_step1,           name='login'),
    path('login/otp/',          views.login_step2_otp,       name='login_otp'),
    path('logout/',             views.logout_view,           name='logout'),
]
