"""
apps/workers/views.py

Web views for the authenticated worker dashboard and account management.

All views require login.  The decorator @login_required(login_url='accounts:login')
is applied individually so URLs stay clean.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator

from .models import WorkerProfile

logger = logging.getLogger(__name__)

login_required_decorator = login_required(login_url='accounts:login')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _worker_required(view_func):
    """Combined: must be logged in AND is_worker=True."""
    @login_required(login_url='accounts:login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_worker:
            messages.error(request, 'This page is for delivery workers only.')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_dashboard_context(request):
    """
    Build the full context dict for the worker dashboard.
    Returns a dict — all keys are used directly in the template.
    """
    user = request.user

    # ── WorkerProfile ─────────────────────────────────────────────────────
    try:
        profile = user.workerprofile
    except WorkerProfile.DoesNotExist:
        # Profile not complete — send them to finish registration
        messages.warning(request, 'Please complete your profile to access the dashboard.')
        return None

    # ── Active policy ─────────────────────────────────────────────────────
    active_policy = None
    try:
        active_policy = user.policies.filter(status='active').latest('start_date')
    except Exception:
        pass

    # ── Recent claims (last 5) ────────────────────────────────────────────
    recent_claims = []
    try:
        recent_claims = user.claims.select_related(
            'disruption_event', 'policy'
        ).order_by('-created_at')[:5]
    except Exception:
        pass

    # ── Recent payouts (last 5) ───────────────────────────────────────────
    recent_payouts = []
    try:
        recent_payouts = user.payouts.order_by('-initiated_at')[:5]
    except Exception:
        pass

    # ── Zone forecast for the current week ───────────────────────────────
    zone_forecast = None
    try:
        if profile.zone:
            zone_forecast = profile.zone.forecasts.order_by('-generated_at').first()
    except Exception:
        pass

    # ── Live Conditions (Weather + AQI) ──────────────────────────────────
    live_conditions = {
        'temp': '--', 'rain': '--', 'aqi': '--',
        'temp_ok': True, 'rain_ok': True, 'aqi_ok': True,
    }
    if profile.zone:
        from apps.triggers.services.weather import WeatherService
        from apps.triggers.services.aqi import AQIService
        try:
            w_data = WeatherService().fetch_weather(profile.zone)
            live_conditions['temp'] = f"{w_data.temp_c:.1f}°C"
            live_conditions['rain'] = f"{w_data.rain_mm:.1f} mm/h"
            live_conditions['temp_ok'] = w_data.temp_c < 42.0
            live_conditions['rain_ok'] = w_data.rain_mm < 35.0
        except Exception: pass
        try:
            a_data = AQIService().fetch_aqi(profile.zone)
            live_conditions['aqi'] = f"{int(a_data.aqi_value)}"
            live_conditions['aqi_ok'] = a_data.aqi_value < 300
        except Exception: pass

    # ── Stats ─────────────────────────────────────────────────────────────
    total_paid_out   = 0
    total_claims     = 0
    approved_claims  = 0
    try:
        from apps.claims.models import Claim
        qs = Claim.objects.filter(worker=user)
        total_claims    = qs.count()
        approved_claims = qs.filter(status='approved').count()
        total_paid_out  = sum(
            p.amount for p in user.payouts.filter(status='credited')
        )
    except Exception:
        pass

    # ── Community Metrics ────────────────────────────────────────────────
    community = {
        'zone_workers_count': 0,
        'circle_members_count': 0,
        'circle_max': 20,
    }
    try:
        if profile.zone:
            community['zone_workers_count'] = profile.zone.workers.count()
            from apps.circles.models import CircleMembership
            circle_membership = CircleMembership.objects.filter(worker=user).first()
            if circle_membership:
                community['circle_members_count'] = circle_membership.circle.members.count()
    except Exception: pass

    # ── Risk Gauge Calculation ───────────────────────────────────────────
    risk_score = profile.risk_score
    risk_percent = min(100, int(risk_score * 100))
    risk_rotation = (risk_percent / 100) * 180 - 90  # For gauge needle

    return {
        'profile':         profile,
        'active_policy':   active_policy,
        'recent_claims':   recent_claims,
        'recent_payouts':  recent_payouts,
        'zone_forecast':   zone_forecast,
        'live_conditions': live_conditions,
        'risk_percent':    risk_percent,
        'risk_rotation':   risk_rotation,
        'community':       community,
        'last_simulation': request.session.get('last_simulation'),
        'total_paid_out':  total_paid_out,
        'total_claims':    total_claims,
        'approved_claims': approved_claims,
        'kyc_status':      profile.kyc_status(),
        'debug':           __import__('django.conf',fromlist=['settings']).settings.DEBUG,
    }


# ─── Dashboard ────────────────────────────────────────────────────────────────

@_worker_required
def dashboard(request):
    """
    Main worker dashboard.
    Shows policy card, stats, recent claims, recent payouts, zone forecast.
    """
    ctx = _get_dashboard_context(request)
    if ctx is None:
        return redirect('accounts:register_profile')
    return render(request, 'workers/dashboard.html', ctx)


# ─── Account Settings ─────────────────────────────────────────────────────────

@_worker_required
def account(request):
    """
    Account settings page.
    Workers can update: name, UPI ID, language, platform, segment, zone.
    Mobile number is read-only (used as USERNAME_FIELD).
    """
    from apps.zones.models import Zone

    user    = request.user
    profile = get_object_or_404(WorkerProfile, user=user)
    zones   = Zone.objects.filter(active=True).order_by('city', 'area_name')

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
        ('bike',    'Bike'),
        ('bicycle', 'Bicycle'),
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

    if request.method == 'POST':
        action = request.POST.get('action', 'profile')

        if action == 'profile':
            name     = request.POST.get('name', '').strip()
            platform = request.POST.get('platform', '').strip()
            segment  = request.POST.get('segment', '').strip()
            zone_id  = request.POST.get('zone', '').strip()
            language = request.POST.get('language', 'en').strip()
            email    = request.POST.get('email', '').strip()

            errors = []
            if not name:
                errors.append('Full name is required.')
            if not platform:
                errors.append('Please select your delivery platform.')

            if errors:
                for e in errors:
                    messages.error(request, e)
            else:
                profile.name     = name
                profile.platform = platform
                profile.segment  = segment
                if zone_id:
                    try:
                        profile.zone = Zone.objects.get(pk=zone_id)
                    except Zone.DoesNotExist:
                        pass
                profile.save()

                user.language = language
                if email:
                    user.email = email
                user.save(update_fields=['language', 'email'])

                messages.success(request, 'Profile updated successfully.')
                return redirect('workers:account')

        elif action == 'upi':
            upi_id = request.POST.get('upi_id', '').strip()
            if not upi_id or '@' not in upi_id:
                messages.error(request, 'Please enter a valid UPI ID (e.g. name@upi).')
            else:
                profile.upi_id = upi_id
                # Clear Razorpay fund account so it is re-created on next payout
                profile.razorpay_fund_acct_id = ''
                profile.save(update_fields=['upi_id', 'razorpay_fund_acct_id'])
                messages.success(
                    request,
                    'UPI ID updated. Your next payout will use the new ID.'
                )
                return redirect('workers:account')

    ctx = {
        'profile':          profile,
        'zones':            zones,
        'platform_choices': PLATFORM_CHOICES,
        'segment_choices':  SEGMENT_CHOICES,
        'language_choices': LANGUAGE_CHOICES,
        'kyc_status':       profile.kyc_status(),
    }
    return render(request, 'workers/account.html', ctx)


# ─── KYC Submit ───────────────────────────────────────────────────────────────

@_worker_required
def kyc_request_otp(request):
    """Step 1 — Worker requests KYC OTP."""
    if request.method != "POST":
        return redirect("workers:account")

    from apps.accounts.kyc_service import request_kyc_otp

    result = request_kyc_otp(request.user)

    if result["success"]:
        messages.success(request, result["message"])
    else:
        messages.error(request, result["message"])

    return redirect("workers:account")


@_worker_required
def kyc_verify_otp(request):
    """Step 2 — Worker submits OTP + Aadhaar to complete KYC."""
    if request.method != "POST":
        return redirect("workers:account")

    from apps.accounts.kyc_service import verify_kyc_otp

    otp_entered = request.POST.get("otp", "").strip()
    aadhaar_raw = request.POST.get("aadhaar", "").strip()

    if not otp_entered:
        messages.error(request, "Please enter the OTP.")
        return redirect("workers:account")

    result = verify_kyc_otp(request.user, otp_entered, aadhaar_raw)

    if result["success"]:
        messages.success(request, result["message"])
    else:
        messages.error(request, result["message"])

    return redirect("workers:account")

from django.http import HttpResponse

@_worker_required
def simulate_trigger(request):
    """
    Developer tool: Simulate a trigger for the worker's zone.
    Only active in DEBUG mode.
    """
    from django.conf import settings
    if not settings.DEBUG:
        messages.error(request, 'This feature is only available in development mode.')
        return redirect('workers:dashboard')

    if request.method != "POST":
        return redirect('workers:dashboard')

    trigger_type = request.POST.get('trigger_type')
    severity = float(request.POST.get('severity', 100.0))

    profile = request.user.workerprofile
    if not profile.zone:
        messages.error(request, 'Please set your zone first.')
        return redirect('workers:dashboard')

    # Trigger the task
    from apps.triggers.tasks import create_manual_event
    from django.utils import timezone
    
    create_manual_event.delay(
        zone_id=profile.zone.id,
        trigger_type=trigger_type,
        severity=severity,
        is_full=True,
        source='simulation_tool'
    )

    # Store simulation info in session for the dashboard to show a log
    request.session['last_simulation'] = {
        'type':      trigger_type.replace('_', ' ').title(),
        'zone':      profile.zone.display_name,
        'time':      timezone.now().strftime('%H:%M:%S'),
        'severity':  severity,
        'steps': [
            f"Manual signal injected: {trigger_type} @ {severity}",
            f"DisruptionEvent created for {profile.zone.display_name}",
            "Asynchronous claim generator queued (Celery)",
            "Fraud detection service awaiting claim data..."
        ]
    }

    messages.success(request, f'Successfully simulated {trigger_type} trigger.')
    return redirect('workers:dashboard')

@_worker_required
def clear_simulation(request):
    """Developer tool: Clear the last simulation log from session."""
    if 'last_simulation' in request.session:
        del request.session['last_simulation']
    return redirect('workers:dashboard')
