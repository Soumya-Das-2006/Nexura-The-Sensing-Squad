"""
apps/payments/webhook.py

Razorpay sends webhook events to /api/v1/payments/webhook/

Handled events
--------------
subscription.charged          → premium payment captured (extends policy + auto-credit circle pool)
subscription.payment_failed   → premium payment failed
payout
