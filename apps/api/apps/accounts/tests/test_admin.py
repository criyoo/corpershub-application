from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken


User = get_user_model()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class UserAdminSplitTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.admin_user)
        self.company_user = User.objects.create_user(
            email="company@example.com",
            password="StrongPass123!",
            role=User.Role.COMPANY,
            email_verified=True,
        )
        self.corper_user = User.objects.create_user(
            email="corper@example.com",
            password="StrongPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )

    def test_company_admin_page_only_lists_company_users(self):
        response = self.client.get(reverse("admin:accounts_companyuser_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.company_user.email)
        self.assertNotContains(response, self.corper_user.email)

    def test_corper_admin_page_only_lists_corper_users(self):
        response = self.client.get(reverse("admin:accounts_corperuser_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.corper_user.email)
        self.assertNotContains(response, self.company_user.email)

    def test_company_admin_add_view_only_offers_company_role(self):
        response = self.client.get(reverse("admin:accounts_companyuser_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{User.Role.COMPANY}"')
        self.assertNotContains(response, f'value="{User.Role.CORPER}"')


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class OutstandingTokenAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(self.admin_user)
        self.token = OutstandingToken.objects.create(
            user=self.admin_user,
            jti="test-outstanding-token-jti",
            token="dummy.jwt.token",
            created_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=1),
        )

    def test_outstanding_token_delete_view_removes_token(self):
        response = self.client.post(
            reverse("admin:token_blacklist_outstandingtoken_delete", args=[self.token.pk]),
            {"post": "yes"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(OutstandingToken.objects.filter(pk=self.token.pk).exists())

    def test_outstanding_token_changelist_exposes_delete_action(self):
        response = self.client.get(reverse("admin:token_blacklist_outstandingtoken_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="delete_selected"')
