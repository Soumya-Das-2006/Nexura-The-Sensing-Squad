"""
apps/admin_portal/views.py

Custom Nexura admin portal — a cleaner alternative to Django admin.
All views require is_admin=True.

/admin-portal/              → overview dashboard (KPIs, recent events)
/admin-portal/workers/      → worker list with search/filter
/admin-portal/claims/       → claims list with approve/reject actions
/admin-portal/payouts/      → payout tracking
/admin-portal/triggers/     → disruption event log
/admin-portal/fraud/        → fraud flags and on-hold claims
/admin-portal/zones/        → zone management
/admin-portal/forecast/     → forecast overview all cities
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def _admin_required(view_func):
    @login_required(login_url='accounts:login')
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_staff or request.user.is_superuser):
            messages.error(request, 'Admin access required.')
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@_admin_required
def dashboard(request):
    from apps.claims.models import Claim
    from apps.payouts.models import Payout
    from apps.policies.models import Policy
    from apps.triggers.models import DisruptionEvent
    from django.contrib.auth import get_user_model
    User = get_user_model()

    now    = timezone.now()
    today  = now.date()
    week   = now - timedelta(days=7)

    ctx = {
        # Totals
        'total_workers':    User.objects.filter(is_worker=True, is_active=True).count(),
        'active_policies':  Policy.objects.filter(status='active').count(),
        'total_paid_out':   Payout.objects.filter(status='credited').aggregate(s=Sum('amount'))['s'] or 0,
        'pending_claims':   Claim.objects.filter(status__in=['pending', 'on_hold']).count(),

        # Recent activity
        'recent_events':    DisruptionEvent.objects.select_related('zone').order_by('-started_at')[:8],
        'recent_claims':    Claim.objects.select_related(
            'worker', 'disruption_event', 'disruption_event__zone'
        ).order_by('-created_at')[:8],
        'recent_payouts':   Payout.objects.select_related('worker').order_by('-initiated_at')[:6],

        # This week
        'week_claims':      Claim.objects.filter(created_at__gte=week).count(),
        'week_payouts':     Payout.objects.filter(
            status='credited', credited_at__gte=week
        ).aggregate(s=Sum('amount'))['s'] or 0,
        'week_triggers':    DisruptionEvent.objects.filter(started_at__gte=week).count(),
    }
    return render(request, 'admin_portal/dashboard.html', ctx)


@_admin_required
def workers_list(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    qs = User.objects.filter(is_worker=True).select_related(
        'workerprofile', 'workerprofile__zone'
    ).order_by('-date_joined')

    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(mobile__icontains=q) | Q(workerprofile__name__icontains=q))

    platform = request.GET.get('platform', '')
    if platform:
        qs = qs.filter(workerprofile__platform=platform)

    ctx = {'workers': qs[:100], 'q': q, 'platform': platform}
    return render(request, 'admin_portal/workers.html', ctx)


@_admin_required
def claims_list(request):
    from apps.claims.models import Claim
    qs = Claim.objects.select_related(
        'worker', 'disruption_event', 'disruption_event__zone', 'policy__plan_tier'
    ).order_by('-created_at')

    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    ctx = {'claims': qs[:100], 'status_filter': status}
    return render(request, 'admin_portal/claims.html', ctx)


@_admin_required
def approve_claim(request, claim_id):
    if request.method != 'POST':
        return redirect('admin_portal:claims')
    from apps.claims.models import Claim
    from apps.claims.tasks import manually_approve_claim
    claim = get_object_or_404(Claim, pk=claim_id)
    if claim.status in ('pending', 'on_hold'):
        manually_approve_claim.delay(claim.pk, request.user.pk)
        messages.success(request, f'Claim #{claim_id} approved. Payout queued.')
    return redirect('admin_portal:claims')


@_admin_required
def reject_claim(request, claim_id):
    if request.method != 'POST':
        return redirect('admin_portal:claims')
    from apps.claims.models import Claim
    from apps.claims.tasks import manually_reject_claim
    claim  = get_object_or_404(Claim, pk=claim_id)
    reason = request.POST.get('reason', 'Rejected by admin.')
    if claim.status in ('pending', 'on_hold'):
        manually_reject_claim.delay(claim.pk, request.user.pk, reason)
        messages.success(request, f'Claim #{claim_id} rejected.')
    return redirect('admin_portal:claims')


@_admin_required
def payouts_list(request):
    from apps.payouts.models import Payout
    qs = Payout.objects.select_related('worker', 'claim').order_by('-initiated_at')
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    ctx = {'payouts': qs[:100], 'status_filter': status}
    return render(request, 'admin_portal/payouts.html', ctx)


@_admin_required
def triggers_list(request):
    from apps.triggers.models import DisruptionEvent
    qs = DisruptionEvent.objects.select_related('zone').order_by('-started_at')[:100]
    ctx = {'events': qs}
    return render(request, 'admin_portal/triggers.html', ctx)


@_admin_required
def fraud_flags_list(request):
    from apps.claims.models import Claim
    qs = Claim.objects.filter(status='on_hold').select_related(
        'worker', 'disruption_event', 'disruption_event__zone'
    ).order_by('-created_at')[:50]
    ctx = {'on_hold_claims': qs}
    return render(request, 'admin_portal/fraud.html', ctx)


@_admin_required
def zones_list(request):
    from apps.zones.models import Zone
    zones = Zone.objects.order_by('city', 'area_name')
    ctx = {'zones': zones}
    return render(request, 'admin_portal/zones.html', ctx)


@_admin_required
def forecast_overview(request):
    from apps.forecasting.models import ZoneForecast
    from apps.forecasting.loader import _next_monday
    from apps.zones.models import Zone
    from datetime import timedelta

    week_start = _next_monday()
    cities     = Zone.objects.filter(active=True).values_list('city', flat=True).distinct()

    forecasts = []
    for city in cities:
        zone = Zone.objects.filter(city=city, active=True).first()
        if zone:
            fc = ZoneForecast.objects.filter(zone=zone, forecast_date=week_start).first()
            if fc:
                forecasts.append(fc)

    ctx = {'forecasts': forecasts, 'week_start': week_start}
    return render(request, 'admin_portal/forecast.html', ctx)


@_admin_required
def fire_test_trigger(request):
    """Admin: manually fire a disruption trigger to test the full claims pipeline."""
    if request.method != 'POST':
        return redirect('admin_portal:dashboard')

    from apps.triggers.models import DisruptionEvent
    from apps.zones.models import Zone

    zone_id      = request.POST.get('zone_id')
    trigger_type = request.POST.get('trigger_type', 'heavy_rain')

    try:
        zone = Zone.objects.get(pk=zone_id)
    except (Zone.DoesNotExist, ValueError):
        messages.error(request, 'Please select a valid zone.')
        return redirect('admin_portal:dashboard')

    severity_map  = {'heavy_rain':42.0,'extreme_heat':44.0,'severe_aqi':320.0,'flash_flood':1.0,'curfew_strike':1.0,'platform_down':120.0}
    threshold_map = {'heavy_rain':35.0,'extreme_heat':42.0,'severe_aqi':300.0,'flash_flood':1.0,'curfew_strike':1.0,'platform_down':60.0}

    event = DisruptionEvent.objects.create(
        zone=zone,
        trigger_type=trigger_type,
        severity_value=severity_map.get(trigger_type, 1.0),
        threshold_value=threshold_map.get(trigger_type, 1.0),
        is_full_trigger=True,
        source_api='admin_test',
    )

    # Try Celery — fall back to direct creation
    try:
        from apps.claims.tasks import process_pending_claims
        process_pending_claims.delay()
        messages.success(request,
            f'✅ Test trigger fired: {event.get_trigger_type_display()} in {zone.display_name}. '
            f'Claims are being queued via Celery. Check the Claims list in a moment.')
    except Exception:
        # Celery not running — run the real pipeline synchronously
        from apps.policies.models import Policy
        from apps.claims.models import Claim
        from apps.claims.pipeline import run_fraud_pipeline
        from apps.payouts.tasks import disburse_payout

        policies = Policy.objects.filter(
            status='active',
            worker__workerprofile__zone=zone
        ).select_related('worker', 'worker__workerprofile', 'plan_tier')

        created_count = 0
        approved_count = 0

        for pol in policies:
            claim, created = Claim.objects.get_or_create(
                worker=pol.worker,
                disruption_event=event,
                defaults={
                    'policy': pol,
                    'payout_amount': pol.weekly_coverage,
                    'status': 'pending',
                }
            )
            if not created:
                continue

            created_count += 1

            # Run the REAL 6-layer fraud pipeline
            result = run_fraud_pipeline(claim)
            decision = result['decision']

            claim.fraud_score = result['fraud_score']
            claim.fraud_flags = result['flags']

            if decision == 'approve':
                claim.status = 'approved'
                approved_count += 1
                claim.save()
                # Queue payout (synchronous in sandbox)
                try:
                    disburse_payout(claim.pk)
                except Exception as pe:
                    logger.warning("[fire_trigger] Payout failed for claim %s: %s", claim.pk, pe)
            elif decision == 'hold':
                claim.status = 'on_hold'
                claim.save()
            else:
                claim.status = 'rejected'
                claim.rejection_reason = result.get('rejection_reason', '')
                claim.save()

        messages.success(request,
            f'✅ Trigger fired: {event.get_trigger_type_display()} in {zone.display_name}. '
            f'{created_count} claim(s) created, {approved_count} auto-approved '
            f'(Celery not running — pipeline ran synchronously).')

    return redirect('admin_portal:claims')


@_admin_required
def kyc_approve(request, user_id):
    """Admin approves a worker's KYC submission."""
    if request.method != 'POST':
        return redirect('admin_portal:workers')

    from apps.accounts.models import KYCRecord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
        kyc = user.kyc
    except (User.DoesNotExist, KYCRecord.DoesNotExist):
        messages.error(request, 'Worker or KYC record not found.')
        return redirect('admin_portal:workers')

    kyc.status = 'approved'
    kyc.verified_at = timezone.now()
    kyc.remarks = request.POST.get('remarks', '')
    kyc.save(update_fields=['status', 'verified_at', 'remarks'])
    messages.success(request, f'KYC approved for {user.display_name}.')
    return redirect('admin_portal:workers')


@_admin_required
def kyc_reject(request, user_id):
    """Admin rejects a worker's KYC submission."""
    if request.method != 'POST':
        return redirect('admin_portal:workers')

    from apps.accounts.models import KYCRecord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(pk=user_id)
        kyc = user.kyc
    except (User.DoesNotExist, KYCRecord.DoesNotExist):
        messages.error(request, 'Worker or KYC record not found.')
        return redirect('admin_portal:workers')

    kyc.status = 'rejected'
    kyc.remarks = request.POST.get('remarks', 'Rejected by admin.')
    kyc.save(update_fields=['status', 'remarks'])
    messages.warning(request, f'KYC rejected for {user.display_name}.')
    return redirect('admin_portal:workers')


@_admin_required
def support_tickets(request):
    """Admin view of all support tickets with ability to respond."""
    from apps.core.models import SupportTicket

    if request.method == 'POST':
        ticket_id  = request.POST.get('ticket_id')
        response   = request.POST.get('admin_response', '').strip()
        new_status = request.POST.get('status', 'resolved')
        try:
            t = SupportTicket.objects.get(pk=ticket_id)
            t.admin_response = response
            t.status = new_status
            t.save()
            messages.success(request, f'Ticket #{ticket_id} updated.')
        except SupportTicket.DoesNotExist:
            messages.error(request, 'Ticket not found.')
        return redirect('admin_portal:support')

    status_filter = request.GET.get('status', '')
    qs = SupportTicket.objects.select_related('worker').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)

    return render(request, 'admin_portal/support.html', {
        'tickets':       qs[:100],
        'status_filter': status_filter,
    })
