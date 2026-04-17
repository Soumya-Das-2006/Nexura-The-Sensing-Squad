"""
apps/accounts/views.py

Web views for authentication flows:
  - Step 1: Enter mobile → send OTP
  - Step 2: Enter OTP → verify
  - Step 3: Complete profile (name, platform, zone, UPI)
  - Login  : mobile → OTP → dashboard
  - Logout

JWT tokens are set as httpOnly cookies for web sessions.
The REST API endpoints live in api_views.py.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import User, OTPRecord, KYCRecord
from .otp_service import generate_otp, verify_otp

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRATION — 3-Step Flow
# ─────────────────────────────────────────────────────────────────────────────

def register_step1_mobile(request):
    """
    STEP 1 — Enter mobile number.
    POST: validates mobile, sends OTP, stores mobile in session, redirects to step 2.
    """
    if request.user.is_authenticated:
        return redirect('workers:dashboard')

    # Pre-fill plan from query string (e.g. ?plan=standard from home CTA)
    plan_slug = request.GET.get('plan', 'standard')

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()

        # Basic validation
        if not mobile or len(mobile) < 10:
            messages.error(request, 'Please enter a valid 10-digit mobile number.')
            return render(request, 'accounts/register_step1.html', {'plan': plan_slug})

        # Normalise — strip +91 prefix if present
        mobile = mobile.lstrip('+').lstrip('91').lstrip('0')
        if len(mobile) != 10 or not mobile.isdigit():
            messages.error(request, 'Please enter a valid 10-digit mobile number without country code.')
            return render(request, 'accounts/register_step1.html', {'plan': plan_slug})

        try:
            generate_otp(mobile, purpose='register')
        except Exception as e:
            logger.error(f"OTP generation failed for {mobile}: {e}")
            messages.error(request, 'Could not send OTP. Please try again in a moment.')
            return render(request, 'accounts/register_step1.html', {'plan': plan_slug})

        # Store in session
        request.session['reg_mobile'] = mobile
        request.session['reg_plan']   = plan_slug
        messages.success(request, f'OTP sent to +91 {mobile}.')

        if settings.OTP_TEST_MODE:
            messages.info(request, f'[TEST MODE] OTP is: {settings.OTP_TEST_CODE}')

        return redirect('accounts:register_otp')

    return render(request, 'accounts/register_step1.html', {'plan': plan_slug})


def register_step2_otp(request):
    """
    STEP 2 — Enter the 6-digit OTP.
    POST: verifies OTP, creates User if new, redirects to step 3 (profile).
    """
    mobile = request.session.get('reg_mobile')
    if not mobile:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('accounts:register')

    if request.method == 'POST':
        # Support both individual digit inputs and a single 'otp' field
        digits = [request.POST.get(f'd{i}', '') for i in range(1, 7)]
        code   = ''.join(digits).strip() or request.POST.get('otp', '').strip()

        if len(code) != 6 or not code.isdigit():
            messages.error(request, 'Please enter the complete 6-digit OTP.')
            return render(request, 'accounts/register_step2.html', {'mobile': mobile})

        ok, reason = verify_otp(mobile, code, purpose='register')

        if not ok:
            error_msgs = {
                'not_found':    'No OTP found. Please request a new one.',
                'expired':      'OTP has expired. Please request a new one.',
                'already_used': 'This OTP has already been used.',
                'max_attempts': 'Too many incorrect attempts. Please request a new OTP.',
                'invalid':      'Incorrect OTP. Please check and try again.',
            }
            messages.error(request, error_msgs.get(reason, 'OTP verification failed.'))
            return render(request, 'accounts/register_step2.html', {'mobile': mobile})

        # Create or retrieve user
        user, created = User.objects.get_or_create(
            mobile=mobile,
            defaults={'is_worker': True, 'mobile_verified': True},
        )
        if not created:
            user.mobile_verified = True
            user.save(update_fields=['mobile_verified'])

        # Also create a KYCRecord if it doesn't exist
        KYCRecord.objects.get_or_create(worker=user)

        # Log the user in via Django session
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)

        request.session['reg_mobile'] = mobile  # keep for step 3

        if user.profile_complete:
            messages.success(request, f'Welcome back, {user.display_name}!')
            return redirect('workers:dashboard')

        return redirect('accounts:register_profile')

    return render(request, 'accounts/register_step2.html', {'mobile': mobile})


def register_step3_profile(request):
    """
    STEP 3 — Complete profile (name, platform, UPI ID).
    This view is also accessible from the worker's account settings page.
    """
    from apps.workers.models import WorkerProfile
    from apps.zones.models import Zone

    if not request.user.is_authenticated:
        return redirect('accounts:login')

    user   = request.user
    zones  = Zone.objects.filter(active=True).order_by('city', 'area_name')
    plan   = request.session.get('reg_plan', 'standard')

    PLATFORM_CHOICES = [
        ('zomato',  'Zomato'),
        ('swiggy',  'Swiggy'),
        ('amazon',  'Amazon Flex'),
        ('zepto',   'Zepto'),
        ('blinkit', 'Blinkit'),
        ('dunzo',   'Dunzo'),
        ('other',   'Other'),
    ]

    SEGMENT_CHOICES = [
        ('bike',    'Bike Rider'),
        ('bicycle', 'Bicycle Rider'),
        ('auto',    'Auto Rickshaw'),
        ('car',     'Car'),
    ]
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'हिंदी (Hindi)'),
        ('mr', 'मराठी (Marathi)'),
        ('bn', 'বাংলা (Bengali)'),
        ('ta', 'தமிழ் (Tamil)'),
        ('te', 'తెలుగు (Telugu)'),
    ]
    allowed_language_codes = {code for code, _ in LANGUAGE_CHOICES}

    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        platform = request.POST.get('platform', '').strip()
        segment  = request.POST.get('segment', 'bike').strip()
        zone_id  = request.POST.get('zone', '').strip()
        upi_id   = request.POST.get('upi_id', '').strip()
        language = request.POST.get('language', 'en').strip().lower()
        if language not in allowed_language_codes:
            language = 'en'

        # Validation
        errors = []
        if not name:
            errors.append('Full name is required.')
        if not platform:
            errors.append('Please select your delivery platform.')
        if not zone_id:
            errors.append('Please select your operating zone.')
        if not upi_id or '@' not in upi_id:
            errors.append('Please enter a valid UPI ID (e.g. name@upi).')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/register_step3.html', {
                'zones': zones, 'platform_choices': PLATFORM_CHOICES,
                'segment_choices': SEGMENT_CHOICES, 'plan': plan,
                'language_choices': LANGUAGE_CHOICES,
            })

        try:
            zone = Zone.objects.get(pk=zone_id)
        except Zone.DoesNotExist:
            messages.error(request, 'Invalid zone selected.')
            return render(request, 'accounts/register_step3.html', {
                'zones': zones, 'platform_choices': PLATFORM_CHOICES,
                'segment_choices': SEGMENT_CHOICES, 'plan': plan,
                'language_choices': LANGUAGE_CHOICES,
            })

        # Create / update WorkerProfile
        profile, _ = WorkerProfile.objects.get_or_create(user=user)
        profile.name     = name
        profile.platform = platform
        profile.segment  = segment
        profile.zone     = zone
        profile.upi_id   = upi_id
        profile.save()

        # Update user language
        user.language        = language
        user.profile_complete = True
        user.save(update_fields=['language', 'profile_complete'])

        # Clear registration session keys
        request.session.pop('reg_mobile', None)

        messages.success(request, f'Welcome to Nexura, {name}! Now choose your protection plan.')
        return redirect('policies:plans')

    return render(request, 'accounts/register_step3.html', {
        'zones':            zones,
        'platform_choices': PLATFORM_CHOICES,
        'segment_choices':  SEGMENT_CHOICES,
        'language_choices': LANGUAGE_CHOICES,
        'plan':             plan,
    })


# ─────────────────────────────────────────────────────────────────────────────
# RESEND OTP
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def resend_otp(request):
    """Resend OTP for an in-progress registration or login."""
    mobile  = request.session.get('reg_mobile') or request.session.get('login_mobile')
    purpose = 'register' if 'reg_mobile' in request.session else 'login'

    if not mobile:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('accounts:register')

    try:
        generate_otp(mobile, purpose=purpose)
        messages.success(request, f'A new OTP has been sent to +91 {mobile}.')
        if settings.OTP_TEST_MODE:
            messages.info(request, f'[TEST MODE] OTP is: {settings.OTP_TEST_CODE}')
    except Exception as e:
        messages.error(request, 'Could not resend OTP. Please try again.')

    if purpose == 'register':
        return redirect('accounts:register_otp')
    return redirect('accounts:login_otp')


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN — 2-Step OTP Flow
# ─────────────────────────────────────────────────────────────────────────────

def login_step1(request):
    """STEP 1 — Enter registered mobile number."""
    if request.user.is_authenticated:
        return redirect('workers:dashboard')

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        mobile = mobile.lstrip('+').lstrip('91').lstrip('0')

        if not mobile or len(mobile) != 10 or not mobile.isdigit():
            messages.error(request, 'Please enter a valid 10-digit mobile number.')
            return render(request, 'accounts/login_step1.html')

        # Check account exists
        if not User.objects.filter(mobile=mobile, is_active=True).exists():
            messages.error(request, 'No account found for this number. Please register first.')
            return render(request, 'accounts/login_step1.html')

        try:
            generate_otp(mobile, purpose='login')
        except Exception:
            messages.error(request, 'Could not send OTP. Please try again.')
            return render(request, 'accounts/login_step1.html')

        request.session['login_mobile'] = mobile
        messages.success(request, f'OTP sent to +91 {mobile}.')
        if settings.OTP_TEST_MODE:
            messages.info(request, f'[TEST MODE] OTP is: {settings.OTP_TEST_CODE}')
        return redirect('accounts:login_otp')

    return render(request, 'accounts/login_step1.html')


def login_step2_otp(request):
    """STEP 2 — Verify OTP and log in."""
    mobile = request.session.get('login_mobile')
    if not mobile:
        return redirect('accounts:login')

    if request.method == 'POST':
        digits = [request.POST.get(f'd{i}', '') for i in range(1, 7)]
        code   = ''.join(digits).strip() or request.POST.get('otp', '').strip()

        ok, reason = verify_otp(mobile, code, purpose='login')
        if not ok:
            error_msgs = {
                'not_found':    'No OTP found. Please request a new one.',
                'expired':      'OTP has expired.',
                'max_attempts': 'Too many attempts. Request a new OTP.',
                'invalid':      'Incorrect OTP.',
            }
            messages.error(request, error_msgs.get(reason, 'Verification failed.'))
            return render(request, 'accounts/login_step2.html', {'mobile': mobile})

        try:
            user = User.objects.get(mobile=mobile, is_active=True)
        except User.DoesNotExist:
            messages.error(request, 'Account not found.')
            return redirect('accounts:login')

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        request.session.pop('login_mobile', None)

        messages.success(request, f'Welcome back, {user.display_name}!')

        next_url = request.GET.get('next', '')
        if next_url:
            return redirect(next_url)
        if user.is_admin or user.is_staff or user.is_superuser:
            return redirect('admin_portal:dashboard')
        return redirect('workers:dashboard')

    return render(request, 'accounts/login_step2.html', {'mobile': mobile})


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

def logout_view(request):
    name = request.user.display_name if request.user.is_authenticated else ''
    auth_logout(request)
    messages.success(request, f'You have been logged out successfully. Stay safe, {name}!')
    return redirect('core:home')
