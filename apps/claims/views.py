"""
apps/claims/views.py

Worker-facing claim views:
  /claims/          → list of all worker's claims
  /claims/<pk>/     → individual claim detail with fraud score breakdown
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Claim

logger = logging.getLogger(__name__)

_login = login_required(login_url='accounts:login')


@_login
def my_claims(request):
    """Paginated list of the current worker's claims."""
    if not request.user.is_worker:
        return redirect('core:home')

    claims = Claim.objects.filter(
        worker=request.user
    ).select_related(
        'disruption_event', 'disruption_event__zone', 'policy', 'policy__plan_tier'
    ).order_by('-created_at')

    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter in ('pending', 'approved', 'rejected', 'on_hold'):
        claims = claims.filter(status=status_filter)

    # Stats
    total        = Claim.objects.filter(worker=request.user).count()
    approved     = Claim.objects.filter(worker=request.user, status='approved').count()
    pending      = Claim.objects.filter(worker=request.user, status='pending').count()
    on_hold      = Claim.objects.filter(worker=request.user, status='on_hold').count()

    ctx = {
        'claims':        claims,
        'status_filter': status_filter,
        'stats': {
            'total':    total,
            'approved': approved,
            'pending':  pending,
            'on_hold':  on_hold,
        },
    }
    return render(request, 'claims/my_claims.html', ctx)


@_login
def claim_detail(request, pk):
    """Individual claim detail — shows fraud score breakdown and payout info."""
    claim = get_object_or_404(Claim, pk=pk, worker=request.user)

    # Payout associated with this claim
    payout = None
    try:
        payout = claim.payout
    except Exception:
        pass

    ctx = {
        'claim':  claim,
        'payout': payout,
    }
    return render(request, 'claims/claim_detail.html', ctx)
