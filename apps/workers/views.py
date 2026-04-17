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

    return {
        'profile':         profile,
        'active_policy':   active_policy,
        'recent_claims':   recent_claims,
        'recent_payouts':  recent_payouts,
        'zone_forecast':   zone_forecast,
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
def kyc_submit(request):
    """
    Worker submits Aadhaar for KYC.
    Aadhaar is immediately hashed — never stored as plaintext.
    """
    from apps.accounts.models import KYCRecord

    if request.method != 'POST':
        return redirect('workers:account')

    aadhaar_raw = request.POST.get('aadhaar', '').replace(' ', '').replace('-', '')
    if len(aadhaar_raw) != 12 or not aadhaar_raw.isdigit():
        messages.error(request, 'Please enter a valid 12-digit Aadhaar number.')
        return redirect('workers:account')

    kyc, _ = KYCRecord.objects.get_or_create(worker=request.user)
    kyc.set_aadhaar(aadhaar_raw)
    kyc.status       = 'submitted'
    kyc.submitted_at = timezone.now()
    kyc.save()

    # Aadhaar is PBKDF2-hashed and stored. Status set to 'submitted' for admin review.
    # UIDAI Aadhaar OTP verification is not available in sandbox.
    # In production, integrate DigiLocker or UIDAI e-KYC API here before auto-approving.
    logger.info("[KYC] Aadhaar submitted for user %s — awaiting admin review.", request.user.mobile)
    messages.success(
        request,
        'KYC submitted successfully. Verification usually completes within 24 hours.'
    )
    return redirect('workers:account')


# ─── API URLs stub ────────────────────────────────────────────────────────────
# Full DRF serializers/views live in api_views.py (below)


@_worker_required
def simulate_trigger(request):
    """DEBUG ONLY: simulate a disruption trigger for the worker's zone."""
    from django.conf import settings as djsettings
    from django.http import HttpResponseForbidden

    if not djsettings.DEBUG:
        return HttpResponseForbidden('Only available in DEBUG mode.')
    if request.method != 'POST':
        return redirect('workers:dashboard')

    from apps.triggers.models import DisruptionEvent
    from apps.claims.models import Claim
    from apps.policies.models import Policy

    user         = request.user
    profile      = user.workerprofile
    trigger_type = request.POST.get('trigger_type', 'heavy_rain')

    if not profile.zone:
        messages.error(request, 'You need to set your operating zone first.')
        return redirect('workers:account')

    severity_map  = {'heavy_rain':42.0,'extreme_heat':44.0,'platform_down':120.0,'severe_aqi':320.0}
    threshold_map = {'heavy_rain':35.0,'extreme_heat':42.0,'platform_down':60.0,'severe_aqi':300.0}

    event = DisruptionEvent.objects.create(
        zone=profile.zone,
        trigger_type=trigger_type,
        severity_value=severity_map.get(trigger_type, 1.0),
        threshold_value=threshold_map.get(trigger_type, 1.0),
        is_full_trigger=True,
        source_api='dev_simulate',
    )

    try:
        policy = user.policies.filter(status='active').latest('start_date')
    except Policy.DoesNotExist:
        messages.error(request, 'You need an active policy to test claim creation. Select a plan first.')
        event.delete()
        return redirect('policies:plans')

    claim, created = Claim.objects.get_or_create(
        worker=user,
        disruption_event=event,
        defaults={
            'policy': policy,
            'payout_amount': policy.weekly_coverage,
            'status': 'pending',
        }
    )

    if created:
        # Run the REAL fraud pipeline, not a hardcoded score
        from apps.claims.pipeline import run_fraud_pipeline
        result = run_fraud_pipeline(claim)
        claim.fraud_score = result['fraud_score']
        claim.fraud_flags = result['flags']
        claim.status = {'approve': 'approved', 'hold': 'on_hold', 'reject': 'rejected'}[result['decision']]
        if result['decision'] == 'reject':
            claim.rejection_reason = result.get('rejection_reason', '')
        claim.save()

        if result['decision'] == 'approve':
            from apps.payouts.tasks import disburse_payout
            try:
                disburse_payout(claim.pk)
            except Exception as pe:
                logger.warning("Payout dispatch failed: %s", pe)

        messages.success(request,
            f'✅ Claim #{claim.pk} created! Fraud score: {claim.fraud_score:.3f}. '
            f'Status: {claim.get_status_display()}')
    else:
        messages.info(request, f'A claim for this event already exists (#{claim.pk}).')

    return redirect('claims:my_claims')
