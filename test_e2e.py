import sys
import os
import django

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexura.settings.development")
django.setup()

from django.contrib.auth import get_user_model
from apps.workers.models import WorkerProfile
from apps.zones.models import Zone
from apps.policies.models import PlanTier, Policy
from apps.triggers.models import DisruptionEvent
from apps.claims.models import Claim
from apps.fraud.service import run_fraud_pipeline
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def run_e2e():
    print("--- Starting E2E Test ---")
    
    # 1. Create a User (Worker)
    mobile = "9998887776"
    user, created = User.objects.get_or_create(mobile=mobile, defaults={'is_worker': True})
    if created:
        user.set_password("123456")
        user.save()
    print(f"User created: {user.mobile}")
    
    # 2. Complete Profile
    zone = Zone.objects.first()
    profile, created = WorkerProfile.objects.get_or_create(user=user, defaults={
        'name': 'E2E Tester',
        'platform': 'zomato',
        'segment': 'bike',
        'zone': zone
    })
    print(f"Profile created: {profile.name} in zone {zone.display_name}")

    # 3. Create a Policy
    plan = PlanTier.objects.first()
    policy, created = Policy.objects.get_or_create(
        worker=user,
        status='active',
        defaults={
            'plan_tier': plan,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timezone.timedelta(days=7)).date(),
            'weekly_coverage': plan.weekly_coverage,
            'weekly_premium': plan.base_premium
        }
    )
    print(f"Policy active: {policy.weekly_coverage} coverage")

    # 4. Fire a Trigger (Event)
    event = DisruptionEvent.objects.create(
        zone=zone,
        trigger_type='heavy_rain',
        severity_value=120.0,
        threshold_value=100.0,
        is_full_trigger=True,
        started_at=timezone.now(),
        ended_at=timezone.now() + timezone.timedelta(hours=2)
    )
    print(f"Event fired: {event.trigger_type} in {zone.display_name}")

    # 5. Generate a Claim
    claim = Claim.objects.create(
        worker=user,
        disruption_event=event,
        policy=policy,
        payout_amount=policy.weekly_coverage * Decimal('0.2')  # say 20% for this event
    )
    print(f"Claim generated: ID {claim.id}, Amount {claim.payout_amount}")

    # 6. Run Fraud Pipeline
    print("Running Fraud Pipeline...")
    run_fraud_pipeline(claim)
    
    # Refresh claim to see status
    claim.refresh_from_db()
    print(f"Claim Status: {claim.status}, Fraud Score: {claim.fraud_score}")
    print("Fraud Flags:")
    for flag in claim.fraud_flag_records.all():
        print(f" - {flag.layer}: {flag.flag_type} ({flag.detail})")

    print("--- E2E Test Completed ---")

if __name__ == "__main__":
    run_e2e()
