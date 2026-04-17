import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.workers.models import WorkerProfile
from apps.zones.models import Zone
from apps.policies.models import PlanTier, Policy
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates demo users, workers, and policies for Nexura.'

    def handle(self, *args, **options):
        # Admins
        admin_mobile = '9000000000'
        if not User.objects.filter(mobile=admin_mobile).exists():
            admin_user = User.objects.create_superuser(mobile=admin_mobile, password='Nexura@demo123')
            admin_user.name = 'Admin User'
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin {admin_mobile}"))

        demo_workers_data = [
            {'mobile': '9876543210', 'name': 'Rahul Sharma (Mumbai)', 'city': 'Mumbai', 'zone_id': 4, 'platform': 'zomato'}, # 4 could be Dadar or similar
            {'mobile': '9123456780', 'name': 'Kiran Rao (Bangalore)', 'city': 'Bangalore', 'zone_id': 20, 'platform': 'swiggy'},
            {'mobile': '9988776655', 'name': 'Aditya Reddy (Hyderabad)', 'city': 'Hyderabad', 'zone_id': 35, 'platform': 'zepto'}
        ]

        # Ensure we have plan tiers
        try:
            standard_plan = PlanTier.objects.filter(name__icontains='Standard').first()
        except Exception:
            standard_plan = None

        for data in demo_workers_data:
            mobile = data['mobile']
            if not User.objects.filter(mobile=mobile).exists():
                user = User.objects.create_user(mobile=mobile, password='Nexura@demo123')
                user.name = data['name']
                user.save()
                
                # KYC
                from apps.accounts.models import KYCRecord
                kyc, _ = KYCRecord.objects.get_or_create(worker=user)
                kyc.status = 'approved'
                kyc.save()

                zone = Zone.objects.filter(city=data['city']).first()
                if not zone:
                    try:
                        zone = Zone.objects.get(pk=data['zone_id'])
                    except Zone.DoesNotExist:
                        zone = None

                profile, _ = WorkerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': data['name'],
                        'platform': data['platform'],
                        'segment': 'bike',
                        'zone': zone,
                        'upi_id': f"{mobile}@ybl",
                        'risk_score': 0.5
                    }
                )

                if standard_plan and not Policy.objects.filter(worker=user).exists():
                    Policy.objects.create(
                        worker=user,
                        plan_tier=standard_plan,
                        start_date=timezone.now().date() - timedelta(days=5),
                        end_date=timezone.now().date() + timedelta(days=2),
                        weekly_premium=standard_plan.base_premium,
                        weekly_coverage=standard_plan.weekly_coverage,
                        status='active'
                    )
                self.stdout.write(self.style.SUCCESS(f"Created demo worker {mobile} with profile and policy."))
            else:
                self.stdout.write(self.style.WARNING(f"Worker {mobile} already exists."))

        self.stdout.write(self.style.SUCCESS("Demo data generation complete."))
