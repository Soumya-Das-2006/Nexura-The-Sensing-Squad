"""apps/circles/views.py"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import RiskCircle, CircleMembership

logger = logging.getLogger(__name__)
_login = login_required(login_url='accounts:login')


@_login
def my_circle(request):
    if not request.user.is_worker:
        return redirect('core:home')
    try:
        profile = request.user.workerprofile
        zone    = profile.zone
    except Exception:
        return redirect('workers:account')

    membership = CircleMembership.objects.filter(
        worker=request.user, is_active=True
    ).select_related('circle', 'circle__zone').first()

    available_circles = []
    if not membership and zone:
        # Simple query — no custom manager needed
        available_circles = RiskCircle.objects.filter(
            zone=zone, is_active=True
        ).order_by('name')

    ctx = {
        'membership':        membership,
        'circle':            membership.circle if membership else None,
        'available_circles': available_circles,
    }
    return render(request, 'circles/my_circle.html', ctx)


@_login
def join_circle(request, circle_id):
    if request.method != 'POST':
        return redirect('circles:my_circle')

    circle = get_object_or_404(RiskCircle, pk=circle_id, is_active=True)

    if circle.is_full:
        messages.error(request, 'This circle is full. Please choose another.')
        return redirect('circles:my_circle')

    # Deactivate any existing memberships in other circles
    CircleMembership.objects.filter(
        worker=request.user, is_active=True
    ).update(is_active=False)

    _, created = CircleMembership.objects.update_or_create(
        worker=request.user, circle=circle,
        defaults={'is_active': True},
    )
    if created:
        messages.success(request, f'You have joined {circle.name}! 🎉')
    else:
        messages.info(request, f'Welcome back to {circle.name}!')
    return redirect('circles:my_circle')


@_login
def leave_circle(request, circle_id):
    if request.method != 'POST':
        return redirect('circles:my_circle')

    CircleMembership.objects.filter(
        worker=request.user, circle_id=circle_id
    ).update(is_active=False)

    messages.success(request, 'You have left the Risk Circle.')
    return redirect('circles:my_circle')
