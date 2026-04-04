"""
apps/payouts/views.py

/payouts/  → payout history for the current worker
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
_login = login_required(login_url='accounts:login')


@_login
def history(request):
    """Payout history — all payouts for the current worker."""
    if not request.user.is_worker:
        return redirect('core:home')

    payouts = request.user.payouts.select_related(
        'claim', 'claim__disruption_event', 'claim__disruption_event__zone',
    ).order_by('-initiated_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        payouts = payouts.filter(status=status_filter)

    total_credited = sum(
        p.amount for p in request.user.payouts.filter(status='credited')
    )

    ctx = {
        'payouts':       payouts,
        'status_filter': status_filter,
        'total_credited': total_credited,
    }
    return render(request, 'payouts/history.html', ctx)
