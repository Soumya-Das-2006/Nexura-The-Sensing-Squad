"""
apps/payments/views.py — worker payment history page
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
_login = login_required(login_url='accounts:login')


@_login
def payment_history(request):
    """List all weekly premium payments for the current worker."""
    if not request.user.is_worker:
        return redirect('core:home')

    payments = request.user.premium_payments.select_related(
        'policy', 'policy__plan_tier'
    ).order_by('-week_start_date')

    total_paid = sum(
        p.amount for p in payments.filter(status__in=['captured', 'grace'])
    )

    ctx = {
        'payments':  payments,
        'total_paid': total_paid,
    }
    return render(request, 'payments/history.html', ctx)
