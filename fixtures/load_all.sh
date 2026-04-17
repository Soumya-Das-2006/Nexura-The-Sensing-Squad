#!/usr/bin/env bash
set -e
echo "Loading Nexura fixtures..."

python manage.py loaddata fixtures/zones.json
echo "  ✓ 73 zones loaded"

python manage.py loaddata fixtures/plans.json
echo "  ✓ 3 plans loaded"

python manage.py loaddata fixtures/risk_circles.json
echo "  ✓ 14 risk circles loaded"

python manage.py shell << 'PYEOF'
from django.utils import timezone
from datetime import timedelta, date
from apps.accounts.models import User, KYCRecord
from apps.workers.models import WorkerProfile
from apps.zones.models import Zone
from apps.policies.models import PlanTier, Policy
from apps.triggers.models import DisruptionEvent
from apps.claims.models import Claim
from apps.payouts.models import Payout
from apps.fraud.models import FraudFlag

# ─── Admin ───────────────────────────────────────────────────
admin, _ = User.objects.get_or_create(mobile='9000000000',
    defaults={'is_admin': True, 'is_staff': True, 'is_superuser': True,
              'mobile_verified': True, 'profile_complete': True})
admin.set_password('Nexura@demo123')
admin.save()
print("  ✓ Admin: 9000000000 / Nexura@demo123")

# ─── Demo Workers ────────────────────────────────────────────
workers_data = [
    {'mobile': '9876543210', 'name': 'Ravi Kumar',    'platform': 'zomato',  'city': 'Mumbai'},
    {'mobile': '9123456780', 'name': 'Priya Sharma',  'platform': 'swiggy',  'city': 'Bangalore'},
    {'mobile': '9988776655', 'name': 'Arjun Singh',   'platform': 'amazon',  'city': 'Delhi'},
]

from apps.accounts.models import KYCRecord
demo_workers = []
for wd in workers_data:
    user, _ = User.objects.get_or_create(mobile=wd['mobile'],
        defaults={'is_worker': True, 'mobile_verified': True, 'profile_complete': True})
    user.set_password('Nexura@demo123')
    user.save()

    zone = Zone.objects.filter(city=wd['city'], active=True).first()
    profile, _ = WorkerProfile.objects.get_or_create(user=user,
        defaults={'name': wd['name'], 'platform': wd['platform'],
                  'segment': 'bike', 'zone': zone,
                  'upi_id': f"{wd['name'].lower().replace(' ','.')}@upi",
                  'risk_score': 0.35})

    kyc, _ = KYCRecord.objects.get_or_create(worker=user)
    if kyc.status not in ('approved', 'verified'):
        kyc.status = 'approved'
        kyc.verified_at = timezone.now()
        kyc.save()

    demo_workers.append((user, profile))
    print(f"  ✓ Worker: {wd['mobile']} ({wd['name']})")

# ─── Policies ────────────────────────────────────────────────
plan_slugs = ['standard', 'premium', 'basic']
today = date.today()
for i, (user, profile) in enumerate(demo_workers):
    plan = PlanTier.objects.filter(slug=plan_slugs[i]).first()
    if not plan:
        continue
    Policy.objects.get_or_create(worker=user, plan_tier=plan,
        defaults={'weekly_premium': plan.base_premium,
                  'weekly_coverage': plan.weekly_coverage,
                  'start_date': today - timedelta(days=7),
                  'end_date': today + timedelta(days=30),
                  'status': 'active',
                  'mandate_confirmed': True})
    print(f"  ✓ Policy: {plan.name} for {user.mobile}")

# ─── Disruption Event ────────────────────────────────────────
mumbai_zone = Zone.objects.filter(city='Mumbai', active=True).first()
event, created = DisruptionEvent.objects.get_or_create(
    zone=mumbai_zone,
    trigger_type='heavy_rain',
    defaults={'severity_value': 42.0, 'threshold_value': 35.0,
              'is_full_trigger': True, 'source_api': 'demo_seed',
              'started_at': timezone.now() - timedelta(hours=2)})
if created:
    print("  ✓ Demo disruption event created (heavy_rain, Mumbai)")

# ─── Demo Claims (approved + credited) ───────────────────────
ravi = User.objects.filter(mobile='9876543210').first()
if ravi:
    policy = ravi.policies.filter(status='active').first()
    claim, created = Claim.objects.get_or_create(
        worker=ravi, disruption_event=event,
        defaults={'policy': policy,
                  'payout_amount': 1000,
                  'fraud_score': 0.12,
                  'status': 'approved',
                  'fraud_flags': [
                      {'layer':1,'flag':'pass','detail':'DisruptionEvent verified','score_contribution':0.0},
                      {'layer':2,'flag':'pass','detail':'No duplicate claim','score_contribution':0.0},
                      {'layer':3,'flag':'pass','detail':'Worker zone matches event zone','score_contribution':0.0},
                      {'layer':4,'flag':'score_approve','detail':'IsolationForest: 0.08 | XGBoost: 0.14 | Ensemble: 0.12','score_contribution':0.12},
                      {'layer':5,'flag':'score_approve','detail':'Score 0.12 < 0.50 — auto-approved','score_contribution':0.12},
                  ]})
    if created:
        print("  ✓ Demo claim created (approved)")
        # Create credited payout
        import uuid
        payout = Payout.objects.create(
            claim=claim, worker=ravi,
            amount=1000, mode='UPI', status='credited',
            razorpay_payout_id=f'pout_{uuid.uuid4().hex[:16]}',
            utr_number=f'UTR{uuid.uuid4().hex[:12].upper()}',
            initiated_at=timezone.now() - timedelta(hours=1, minutes=47),
            credited_at=timezone.now() - timedelta(minutes=13))
        print(f"  ✓ Demo payout created (UTR: {payout.utr_number})")

print()
print("✅ Demo data loaded successfully!")
print("   Admin:      9000000000 / Nexura@demo123")
print("   Worker 1:   9876543210 / Nexura@demo123 (Mumbai, Standard, has credited payout)")
print("   Worker 2:   9123456780 / Nexura@demo123 (Bangalore, Premium)")
print("   Worker 3:   9988776655 / Nexura@demo123 (Delhi, Basic)")
PYEOF
