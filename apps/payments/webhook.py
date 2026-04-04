"""
apps/payments/webhook.py

Razorpay sends webhook events to /api/v1/payments/webhook/

Handled events
--------------
subscription.charged          → premium payment captured
subscription.payment_failed   → premium payment failed
payout.processed              → UPI payout credited (updates apps.payouts.Payout)
payout.failed                 → UPI payout failed
payment.captured              → one-time payment captured (plan purchase)

All payloads are verified using HMAC-SHA256 before processing.
Unhandled events return 200 OK (Razorpay requires 2xx to stop retrying).
"""
import json
import logging
import hmac
import hashlib

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)


def _verify_signature(payload_bytes: bytes, signature: str) -> bool:
    """Return True if the X-Razorpay-Signature header is valid."""
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        logger.warning("[webhook] RAZORPAY_WEBHOOK_SECRET not set — skipping verification.")
        return True   # allow in sandbox/dev
    expected = hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    """
    POST /api/v1/payments/webhook/

    Razorpay sends all subscription and payout events here.
    """

    def post(self, request):
        payload_bytes = request.body
        signature     = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')

        if not _verify_signature(payload_bytes, signature):
            logger.warning("[webhook] Invalid Razorpay signature — rejected.")
            return JsonResponse({'error': 'Invalid signature'}, status=400)

        try:
            payload = json.loads(payload_bytes)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        event = payload.get('event', '')
        data  = payload.get('payload', {})

        logger.info("[webhook] Received event: %s", event)

        handlers = {
            'subscription.charged':        self._handle_subscription_charged,
            'subscription.payment_failed': self._handle_subscription_failed,
            'payout.processed':            self._handle_payout_processed,
            'payout.failed':               self._handle_payout_failed,
            'payment.captured':            self._handle_payment_captured,
        }

        handler = handlers.get(event)
        if handler:
            try:
                handler(data)
            except Exception as exc:
                logger.error("[webhook] Handler for %s raised: %s", event, exc, exc_info=True)
                # Return 200 so Razorpay doesn't retry — we'll fix manually
        else:
            logger.debug("[webhook] No handler for event: %s", event)

        return HttpResponse(status=200)

    # ── subscription.charged ─────────────────────────────────────────────

    def _handle_subscription_charged(self, data: dict):
        """Razorpay successfully debited the weekly premium."""
        from .models import PremiumPayment
        from apps.policies.models import Policy
        from datetime import timedelta

        sub    = data.get('subscription', {}).get('entity', {})
        pay    = data.get('payment', {}).get('entity', {})
        sub_id = sub.get('id', '')
        pay_id = pay.get('id', '')
        amount = pay.get('amount', 0) / 100   # paise → ₹
        sig    = data.get('payment', {}).get('entity', {}).get('razorpay_signature', '')

        try:
            payment = PremiumPayment.objects.filter(
                razorpay_subscription_id=sub_id,
                status='pending',
            ).latest('created_at')
        except PremiumPayment.DoesNotExist:
            logger.warning("[webhook] No pending payment for subscription %s", sub_id)
            return

        payment.capture(razorpay_payment_id=pay_id, signature=sig)

        # Extend policy end date by 7 days
        try:
            policy = payment.policy
            policy.end_date = policy.end_date + timedelta(days=7)
            policy.status   = 'active'
            policy.save(update_fields=['end_date', 'status'])
            logger.info(
                "[webhook] subscription.charged — policy %s extended to %s",
                policy.pk, policy.end_date,
            )

            from .tasks import _notify_payment_captured
            _notify_payment_captured(policy, amount)

        except Exception as e:
            logger.error("[webhook] Could not extend policy: %s", e)

    # ── subscription.payment_failed ──────────────────────────────────────

    def _handle_subscription_failed(self, data: dict):
        """Razorpay failed to debit the weekly premium."""
        from .models import PremiumPayment
        from .tasks import handle_payment_failure

        sub    = data.get('subscription', {}).get('entity', {})
        sub_id = sub.get('id', '')
        reason = data.get('payment', {}).get('entity', {}).get(
            'error_description', 'Auto-debit failed'
        )

        try:
            payment = PremiumPayment.objects.filter(
                razorpay_subscription_id=sub_id,
                status='pending',
            ).latest('created_at')
        except PremiumPayment.DoesNotExist:
            logger.warning("[webhook] No pending payment for subscription %s", sub_id)
            return

        handle_payment_failure.delay(payment.policy_id, payment.pk, reason)
        logger.warning(
            "[webhook] subscription.payment_failed for sub %s — reason: %s",
            sub_id, reason,
        )

    # ── payout.processed ─────────────────────────────────────────────────

    def _handle_payout_processed(self, data: dict):
        """Razorpay successfully credited the worker's UPI."""
        from apps.payouts.models import Payout

        payout_entity = data.get('payout', {}).get('entity', {})
        rp_payout_id  = payout_entity.get('id', '')
        utr           = payout_entity.get('utr', '')

        try:
            payout = Payout.objects.get(razorpay_payout_id=rp_payout_id)
        except Payout.DoesNotExist:
            logger.warning("[webhook] Payout not found for rp_id %s", rp_payout_id)
            return

        if payout.status != 'credited':
            payout.mark_credited(utr=utr, razorpay_id=rp_payout_id)
            logger.info(
                "[webhook] payout.processed — Payout #%s credited UTR=%s",
                payout.pk, utr,
            )

            try:
                from apps.notifications.tasks import send_payout_notification
                send_payout_notification.delay(payout.pk, 'credited')
            except Exception:
                pass

    # ── payout.failed ────────────────────────────────────────────────────

    def _handle_payout_failed(self, data: dict):
        """Razorpay failed to credit the worker's UPI."""
        from apps.payouts.models import Payout

        payout_entity  = data.get('payout', {}).get('entity', {})
        rp_payout_id   = payout_entity.get('id', '')
        error_desc     = payout_entity.get('error', {}).get('description', 'Razorpay payout failed')

        try:
            payout = Payout.objects.get(razorpay_payout_id=rp_payout_id)
        except Payout.DoesNotExist:
            logger.warning("[webhook] Payout not found for rp_id %s", rp_payout_id)
            return

        if payout.status not in ('failed', 'reversed'):
            payout.mark_failed(reason=error_desc)
            logger.warning(
                "[webhook] payout.failed — Payout #%s — reason: %s",
                payout.pk, error_desc,
            )

            try:
                from apps.notifications.tasks import send_payout_notification
                send_payout_notification.delay(payout.pk, 'failed')
            except Exception:
                pass

    # ── payment.captured (one-time plan purchase) ─────────────────────────

    def _handle_payment_captured(self, data: dict):
        """One-time Razorpay payment captured (used for plan-purchase checkout)."""
        pay    = data.get('payment', {}).get('entity', {})
        pay_id = pay.get('id', '')
        amount = pay.get('amount', 0) / 100
        notes  = pay.get('notes', {})
        policy_id = notes.get('policy_id')

        if not policy_id:
            logger.debug("[webhook] payment.captured — no policy_id in notes.")
            return

        try:
            from apps.policies.models import Policy
            policy = Policy.objects.get(pk=policy_id)
            if policy.status == 'pending':
                policy.status            = 'active'
                policy.mandate_confirmed = True
                policy.save(update_fields=['status', 'mandate_confirmed'])
                logger.info(
                    "[webhook] payment.captured — Policy #%s activated (₹%s)",
                    policy_id, amount,
                )
        except Exception as e:
            logger.error("[webhook] Could not activate policy %s: %s", policy_id, e)
