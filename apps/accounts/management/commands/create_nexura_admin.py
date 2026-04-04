from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a Nexura admin user. Login via OTP at /login/.'

    def handle(self, *args, **options):
        User = get_user_model()
        mobile = input('Mobile number (10 digits, no +91): ').strip()
        if not mobile.isdigit() or len(mobile) != 10:
            self.stderr.write(self.style.ERROR('Invalid mobile number. Must be 10 digits.'))
            return

        user, created = User.objects.get_or_create(
            mobile=mobile,
            defaults={
                'is_admin':       True,
                'is_staff':       True,
                'is_worker':      False,
                'is_superuser':   True,
                'mobile_verified': True,
                'profile_complete': True,
            }
        )
        if not created:
            user.is_admin       = True
            user.is_staff       = True
            user.is_superuser   = True
            user.mobile_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ User {mobile} promoted to admin.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Admin user {mobile} created.\n'
                f'   Login at /login/ → enter {mobile} → OTP: 123456 (test mode)\n'
                f'   Admin portal: /admin-portal/'
            ))
