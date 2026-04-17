from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User, USER_LANGUAGE_CHOICES
from apps.workers.models import WorkerProfile
from apps.zones.models import Zone


class RegisterLanguageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            mobile='9999999999',
            password='testpass123',
            is_worker=True,
            mobile_verified=True,
        )
        self.client.force_login(self.user)
        self.zone = Zone.objects.create(city='Pune', area_name='Kothrud', active=True)
        self.url = reverse('accounts:register_profile')

    def _payload(self, language):
        return {
            'name': 'Test Worker',
            'platform': 'zomato',
            'segment': 'bike',
            'zone': str(self.zone.pk),
            'upi_id': 'worker@upi',
            'language': language,
        }

    def test_invalid_language_falls_back_to_english(self):
        response = self.client.post(self.url, data=self._payload('xx'))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'en')

    def test_valid_language_is_saved(self):
        response = self.client.post(self.url, data=self._payload('te'))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'te')
        self.assertTrue(
            WorkerProfile.objects.filter(user=self.user, zone=self.zone).exists()
        )

    def test_registration_template_uses_shared_language_choices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['language_choices'], USER_LANGUAGE_CHOICES)
