"""
apps/notifications/tasks.py

All notification Celery tasks — called by other apps, never directly by users.

Task registry
-------------
send_claim_notification(claim_id, event_type)
    → WhatsApp + email on claim_approved / claim_under_review / claim_rejected

send_payout_notification(payout_id, event_type)
    → WhatsApp + email on credited / failed

send_payment_notification(worker_id, event_type, extra)
    → WhatsApp on payment_captured / payment_failed / grace_used

send_forecast_notification(worker_id, forecast_id)
    → WhatsApp (+ email if Premium plan) with zone risk forecast

send_premium_update_notification(worker_id, data)
    → WhatsApp when weekly premium changes by ≥20%

send_admin_alert(alert_type, data)
    → Email to ADMINS on critical events (fraud rescan, etc.)

All tasks are idempotent — retry-safe.
"""
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .channels import whatsapp, email, get_message, build_email_html

logger = logging.getLogger(__name__)

ADMIN_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@nexaura.in')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_worker(worker_id: int):
    """Fetch a User instance safely."""
    from django.contrib.auth import get_user_model
    try:
        return get_user_model().objects.get(pk=worker_id, is_worker=True)
    except Exception:
        return None


def _lang(worker) -> str:
    """Return the worker's preferred language, fallback to 'en'."""
    return getattr(worker, 'language', 'en') or 'en'


def _upi(worker) -> str:
    try:
        return worker.workerprofile.upi_id or '—'
    except Exception:
        return '—'


# ─── Claim notifications ──────────────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_claim_notification',
             max_retries=3, default_retry_delay=30)
def send_claim_notification(claim_id: int, event_type: str):
    """
    Send notification to a worker about their claim status change.
    event_type: 'claim_approved' | 'claim_under_review' | 'claim_rejected'
    """
    from apps.claims.models import Claim

    try:
        claim  = Claim.objects.select_related(
            'worker', 'worker__workerprofile',
            'disruption_event', 'disruption_event__zone',
        ).get(pk=claim_id)
    except Claim.DoesNotExist:
        logger.error("[notify] Claim %s not found.", claim_id)
        return

    worker = claim.worker
    lang   = _lang(worker)
    upi    = _upi(worker)

    kwargs = {
        'claim_id': claim.pk,
        'amount':   int(claim.payout_amount),
        'trigger':  claim.disruption_event.get_trigger_type_display() if claim.disruption_event else '—',
        'zone':     str(claim.disruption_event.zone) if claim.disruption_event else '—',
        'upi_id':   upi,
        'reason':   claim.rejection_reason or 'Fraud detection flagged this claim.',
    }

    # WhatsApp
    body = get_message(event_type, lang, **kwargs)
    if body:
        whatsapp.send_text(worker.mobile, body)

    # Email (if worker has an email address)
    if worker.email and event_type in ('claim_approved', 'claim_rejected'):
        subject = {
            'claim_approved': f"✅ Your Nexura claim of ₹{kwargs['amount']} has been approved",
            'claim_rejected': f"❌ Your Nexura claim #{claim_id} was not approved",
        }.get(event_type, 'Nexura Claim Update')

        html = build_email_html(subject, f"<p>{body.replace(chr(10), '<br>')}</p>")
        email.send(worker.email, subject, html, plain_body=body)

    logger.info("[notify] %s → %s (worker=%s)", event_type, claim_id, worker.mobile)


# ─── Payout notifications ─────────────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_payout_notification',
             max_retries=3, default_retry_delay=30)
def send_payout_notification(payout_id: int, event_type: str):
    """
    Send notification about a payout status.
    event_type: 'credited' | 'failed'
    """
    from apps.payouts.models import Payout

    try:
        payout = Payout.objects.select_related('worker', 'worker__workerprofile').get(pk=payout_id)
    except Payout.DoesNotExist:
        logger.error("[notify] Payout %s not found.", payout_id)
        return

    worker = payout.worker
    lang   = _lang(worker)
    upi    = _upi(worker)

    if event_type == 'credited':
        kwargs = {
            'amount': int(payout.amount),
            'upi_id': upi,
            'utr':    payout.utr_number or '—',
            'time':   (payout.credited_at or timezone.now()).strftime('%d %b %Y %H:%M'),
        }
        body = get_message('payout_credited', lang, **kwargs)

        if worker.email:
            subject = f"💸 ₹{kwargs['amount']} credited to your UPI — Nexura"
            html = build_email_html(subject, f"""
                <h2 style="color:#22c55e;">₹{kwargs['amount']} Credited ✓</h2>
                <p>Your Nexura payout has been successfully credited.</p>
                <table style="width:100%;border-collapse:collapse;">
                  <tr><td style="padding:8px 0;color:#64748b;">Amount</td>
                      <td style="padding:8px 0;font-weight:700;">₹{kwargs['amount']}</td></tr>
                  <tr><td style="padding:8px 0;color:#64748b;">UPI</td>
                      <td style="padding:8px 0;">{upi}</td></tr>
                  <tr><td style="padding:8px 0;color:#64748b;">UTR</td>
                      <td style="padding:8px 0;font-family:monospace;">{kwargs['utr']}</td></tr>
                  <tr><td style="padding:8px 0;color:#64748b;">Time</td>
                      <td style="padding:8px 0;">{kwargs['time']}</td></tr>
                </table>
            """)
            email.send(worker.email, subject, html)

    else:  # failed
        kwargs = {
            'amount': int(payout.amount),
            'upi_id': upi,
            'reason': payout.failure_reason or 'Bank transfer failed.',
        }
        body = get_message('payout_failed', lang, **kwargs)

    if body:
        whatsapp.send_text(worker.mobile, body)

    logger.info("[notify] payout_%s → %s (worker=%s)", event_type, payout_id, worker.mobile)


# ─── Payment notifications ────────────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_payment_notification',
             max_retries=3, default_retry_delay=30)
def send_payment_notification(worker_id: int, event_type: str, extra: dict = None):
    """
    Send premium payment notification.
    event_type: 'payment_captured' | 'payment_failed' | 'grace_used'
    """
    worker = _get_worker(worker_id)
    if not worker:
        return

    lang  = _lang(worker)
    extra = extra or {}

    kwargs = {
        'amount': extra.get('amount', '—'),
        'reason': extra.get('reason', 'Payment declined by bank.'),
    }

    body = get_message(event_type, lang, **kwargs)
    if body:
        whatsapp.send_text(worker.mobile, body)

    logger.info("[notify] %s → worker=%s", event_type, worker.mobile)


# ─── Forecast notifications ───────────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_forecast_notification',
             max_retries=2, default_retry_delay=60)
def send_forecast_notification(worker_id: int, forecast_id: int):
    """
    Send weekly risk forecast WhatsApp message to a worker.
    """
    from apps.forecasting.models import ZoneForecast

    worker = _get_worker(worker_id)
    if not worker:
        return

    try:
        forecast = ZoneForecast.objects.select_related('zone').get(pk=forecast_id)
    except ZoneForecast.DoesNotExist:
        logger.error("[notify] Forecast %s not found.", forecast_id)
        return

    lang = _lang(worker)

    risk_advice = {
        'Low':      'Low risk week ahead. Keep delivering!',
        'Moderate': 'Some disruption possible. Stay alert for trigger alerts.',
        'High':     '⚠️ High disruption risk! You may receive auto-claims this week.',
        'Critical': '🚨 Critical risk! Very likely to trigger auto-claims. Stay safe.',
    }.get(forecast.overall_risk_level, '')

    kwargs = {
        'zone':  forecast.zone.display_name,
        'week':  forecast.forecast_date.strftime('%d %b %Y'),
        'rain':  int(forecast.rain_probability * 100),
        'heat':  int(forecast.heat_probability * 100),
        'aqi':   int(forecast.aqi_probability  * 100),
        'level': forecast.overall_risk_level,
        'advice': risk_advice,
    }

    body = get_message('forecast', lang, **kwargs)
    if body:
        whatsapp.send_text(worker.mobile, body)

    # Premium-plan workers also get email
    try:
        active_policy = worker.policies.filter(status='active').latest('start_date')
        if active_policy.plan_tier.slug == 'premium' and worker.email:
            subject = f"🌦️ Weekly Risk Forecast — {forecast.zone.city} — {forecast.overall_risk_level} Risk"
            html = build_email_html(subject, f"""
                <h2>Weekly Disruption Forecast</h2>
                <h3 style="color:#015fc9;">{forecast.zone.display_name}</h3>
                <p>Week of <strong>{kwargs['week']}</strong></p>
                <table style="width:100%;border-collapse:collapse;">
                  <tr><td style="padding:8px 0;">☔ Rain risk</td>
                      <td style="padding:8px 0;font-weight:700;">{kwargs['rain']}%</td></tr>
                  <tr><td style="padding:8px 0;">🌡️ Heat risk</td>
                      <td style="padding:8px 0;font-weight:700;">{kwargs['heat']}%</td></tr>
                  <tr><td style="padding:8px 0;">🌫️ AQI risk</td>
                      <td style="padding:8px 0;font-weight:700;">{kwargs['aqi']}%</td></tr>
                  <tr style="border-top:2px solid #e2e8f0;">
                    <td style="padding:12px 0;font-weight:700;">Overall Risk</td>
                    <td style="padding:12px 0;font-weight:900;color:#015fc9;">
                        {forecast.overall_risk_level}
                    </td>
                  </tr>
                </table>
                <p style="color:#64748b;">{risk_advice}</p>
            """)
            email.send(worker.email, subject, html)
    except Exception:
        pass

    logger.info("[notify] forecast → worker=%s zone=%s", worker.mobile, forecast.zone)


# ─── Premium update notification ─────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_premium_update_notification',
             max_retries=2)
def send_premium_update_notification(worker_id: int, data: dict):
    """Notify worker that their weekly premium has been recalculated."""
    worker = _get_worker(worker_id)
    if not worker:
        return

    lang = _lang(worker)
    kwargs = {
        'old':  int(data.get('old', 0)),
        'new':  int(data.get('new', 0)),
        'risk': float(data.get('risk', 0)),
    }

    body = get_message('premium_updated', lang, **kwargs)
    if body:
        whatsapp.send_text(worker.mobile, body)

    logger.info(
        "[notify] premium_updated → worker=%s ₹%s→₹%s",
        worker.mobile, kwargs['old'], kwargs['new'],
    )


# ─── Admin alerts ─────────────────────────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.send_admin_alert', max_retries=2)
def send_admin_alert(alert_type: str, data: dict):
    """
    Send an email alert to the admin address for critical system events.
    e.g. fraud_rescan_flag, payout_threshold_exceeded, etc.
    """
    subjects = {
        'fraud_rescan_flag':  '🚨 Nexura: Fraud Rescan Flag — Claim requires review',
        'payout_failure':     '⚠️ Nexura: Payout failure requires attention',
    }
    subject = subjects.get(alert_type, f'Nexura Admin Alert: {alert_type}')

    rows = ''.join(
        f"<tr><td style='padding:6px 12px;color:#64748b;'>{k}</td>"
        f"<td style='padding:6px 12px;font-weight:600;'>{v}</td></tr>"
        for k, v in data.items()
    )
    body_html = f"""
        <h2 style="color:#dc2626;">{subject}</h2>
        <table style="border-collapse:collapse;width:100%;">{rows}</table>
        <p style="margin-top:20px;color:#64748b;font-size:13px;">
          Review in the <a href="/django-admin/claims/claim/">Django admin</a>.
        </p>
    """
    html = build_email_html(subject, body_html)
    email.send(ADMIN_EMAIL, subject, html)
    logger.info("[notify] admin_alert: %s", alert_type)


# ─── WhatsApp webhook verification ───────────────────────────────────────────

@shared_task(name='apps.notifications.tasks.process_whatsapp_webhook')
def process_whatsapp_webhook(payload: dict):
    """
    Process incoming WhatsApp webhook messages (e.g. worker replies).
    Currently logs only — extend to handle support queries.
    """
    try:
        entries = payload.get('entry', [])
        for entry in entries:
            for change in entry.get('changes', []):
                value    = change.get('value', {})
                messages = value.get('messages', [])
                for msg in messages:
                    mobile  = msg.get('from', '')[2:]   # strip 91 prefix
                    text    = msg.get('text', {}).get('body', '')
                    logger.info("[WhatsApp] Incoming from +91%s: %s", mobile, text[:100])
    except Exception as exc:
        logger.error("[WhatsApp webhook] Processing error: %s", exc)
