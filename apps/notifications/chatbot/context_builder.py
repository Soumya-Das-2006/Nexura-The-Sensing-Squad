"""
apps/notifications/chatbot/context_builder.py

Fetches real user data from the Nexura DB to populate response templates.

Each function returns a dict of placeholders that get_response() accepts.
All functions are safe — they return sensible defaults on any DB error
so the chatbot never crashes due to missing data.
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def _fmt_amount(amount) -> str:
    """Format numeric amount as Indian number string."""
    try:
        return f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_date(dt) -> str:
    if dt is None:
        return "—"
    try:
        if hasattr(dt, 'strftime'):
            return dt.strftime("%d %b %Y")
        return str(dt)
    except Exception:
        return "—"


def get_user_by_phone(phone: str):
    """Return User object for the given phone number, or None."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Strip +91 / 91 prefix for DB lookup
        digits = phone.lstrip('+').lstrip('91') if len(phone) >= 10 else phone
        return (
            User.objects.filter(phone=digits).first() or
            User.objects.filter(phone=phone).first()
        )
    except Exception as exc:
        logger.warning("[ContextBuilder] get_user_by_phone failed: %s", exc)
        return None


def base_context(user) -> dict:
    """Common placeholders used by most responses."""
    if user is None:
        return {'name': 'Friend'}
    return {
        'name': user.first_name or user.get_full_name() or 'Friend',
    }


def balance_context(user) -> dict:
    """Fetch wallet/account balance for the user."""
    ctx = base_context(user)
    ctx['balance'] = '—'
    if user is None:
        return ctx
    try:
        # Nexura stores balance on WorkerProfile
        profile = user.workerprofile
        ctx['balance'] = _fmt_amount(getattr(profile, 'wallet_balance', 0))
    except Exception:
        ctx['balance'] = '0.00'
    return ctx


def claim_context(user) -> dict:
    """Fetch latest claim status for the user."""
    ctx = base_context(user)
    ctx.update({'claim_id': '—', 'claim_status': '—'})
    if user is None:
        return ctx
    try:
        from apps.claims.models import Claim
        claim = (
            Claim.objects
            .filter(worker=user)
            .order_by('-created_at')
            .first()
        )
        if claim:
            ctx['claim_id']     = str(claim.pk)
            ctx['claim_status'] = claim.get_status_display() if hasattr(claim, 'get_status_display') else claim.status
        else:
            ctx['claim_id']     = 'No claim found'
            ctx['claim_status'] = '—'
    except Exception as exc:
        logger.warning("[ContextBuilder] claim_context failed: %s", exc)
    return ctx


def policy_context(user) -> dict:
    """Fetch active policy for the user."""
    ctx = base_context(user)
    ctx.update({'policy_no': '—', 'coverage': '—'})
    if user is None:
        return ctx
    try:
        from apps.policies.models import Policy
        policy = (
            Policy.objects
            .filter(worker=user, is_active=True)
            .order_by('-created_at')
            .first()
        )
        if policy:
            ctx['policy_no'] = getattr(policy, 'policy_number', str(policy.pk))
            ctx['coverage']  = _fmt_amount(getattr(policy, 'coverage_amount', 0))
    except Exception as exc:
        logger.warning("[ContextBuilder] policy_context failed: %s", exc)
    return ctx


def payout_context(user) -> dict:
    """Fetch latest payout details for the user."""
    ctx = base_context(user)
    ctx.update({'payout_amount': '—', 'payout_date': '—'})
    if user is None:
        return ctx
    try:
        from apps.payouts.models import Payout
        payout = (
            Payout.objects
            .filter(worker=user)
            .order_by('-created_at')
            .first()
        )
        if payout:
            ctx['payout_amount'] = _fmt_amount(getattr(payout, 'amount', 0))
            ctx['payout_date']   = _fmt_date(getattr(payout, 'expected_date', None)
                                             or getattr(payout, 'created_at', None))
    except Exception as exc:
        logger.warning("[ContextBuilder] payout_context failed: %s", exc)
    return ctx


def payment_context(user) -> dict:
    """Fetch upcoming payment / EMI details."""
    ctx = base_context(user)
    ctx.update({'amount': '—', 'due_date': '—'})
    if user is None:
        return ctx
    try:
        # Try to get the next premium due from the active policy
        from apps.policies.models import Policy
        policy = (
            Policy.objects
            .filter(worker=user, is_active=True)
            .order_by('-created_at')
            .first()
        )
        if policy:
            ctx['amount']   = _fmt_amount(getattr(policy, 'premium_amount', 0))
            ctx['due_date'] = _fmt_date(getattr(policy, 'next_due_date', None))
    except Exception as exc:
        logger.warning("[ContextBuilder] payment_context failed: %s", exc)
    return ctx


# Intent → context builder mapping
CONTEXT_BUILDERS = {
    'check_balance':      balance_context,
    'check_claim_status': claim_context,
    'check_policy':       policy_context,
    'check_payout':       payout_context,
    'make_payment':       payment_context,
    'get_statement':      base_context,
    'report_problem':     base_context,
    'get_help':           base_context,
    'greet':              base_context,
    'farewell':           base_context,
    'unknown':            base_context,
}


def build_context(intent_name: str, user) -> dict:
    """
    Build the context dict for the given intent and user.

    Parameters
    ----------
    intent_name : Detected intent string
    user        : Django User instance (may be None for unregistered users)

    Returns
    -------
    dict of placeholder values for response formatting
    """
    builder = CONTEXT_BUILDERS.get(intent_name, base_context)
    return builder(user)
