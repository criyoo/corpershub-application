from django.core import mail
from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.adminpanel.models import AdminRegistrationRequest


class AdminRegistrationAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def create_admin_user(self, email: str = "admin@corpershub.ng") -> User:
        return User.objects.create_user(
            email=email,
            password="AdminPass123!",
            role=User.Role.ADMIN,
            email_verified=True,
            is_active=True,
        )

    def submit_admin_registration(self, email: str, password: str = "AdminPass123!"):
        response = self.client.post(
            "/api/auth/admin/register/",
            {
                "email": email,
                "password": password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "otp_sent")
        self.assertEqual(response.data["email"], email)
        return response

    def verify_admin_registration(self, email: str, code: str = "A1B2C3"):
        return self.client.post(
            "/api/auth/admin/register/verify/",
            {
                "email": email,
                "code": code,
            },
            format="json",
        )

    def test_public_register_endpoint_rejects_admin_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "platform-admin@example.com",
                "password": "AdminPass123!",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="platform-admin@example.com").exists())

    def test_first_admin_registration_creates_admin_user_immediately(self):
        self.submit_admin_registration("first-admin@example.com")
        response = self.verify_admin_registration("first-admin@example.com")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "created")
        user = User.objects.get(email="first-admin@example.com")
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.is_staff)
        self.assertEqual(AdminRegistrationRequest.objects.count(), 0)

    def test_subsequent_admin_registration_creates_pending_request_and_notifies_first_admin(self):
        first_admin = self.create_admin_user()
        self.submit_admin_registration("second-admin@example.com")
        mail.outbox.clear()

        response = self.verify_admin_registration("second-admin@example.com")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "pending")
        request = AdminRegistrationRequest.objects.get(email="second-admin@example.com")
        self.assertEqual(request.status, AdminRegistrationRequest.Status.PENDING)
        self.assertFalse(User.objects.filter(email="second-admin@example.com").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [first_admin.email])

    def test_admin_can_approve_pending_admin_registration_request(self):
        first_admin = self.create_admin_user()
        self.submit_admin_registration("new-admin@example.com")
        mail.outbox.clear()
        response = self.verify_admin_registration("new-admin@example.com")
        request = AdminRegistrationRequest.objects.get(email="new-admin@example.com")
        self.assertEqual(response.status_code, 202)
        mail.outbox.clear()

        self.client.force_authenticate(user=first_admin)
        approval_response = self.client.patch(
            f"/api/adminpanel/admin-registration-requests/{request.id}/",
            {"status": "approved"},
            format="json",
        )

        self.assertEqual(approval_response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, AdminRegistrationRequest.Status.APPROVED)
        self.assertEqual(request.reviewed_by_id, first_admin.id)
        approved_user = User.objects.get(email="new-admin@example.com")
        self.assertEqual(approved_user.role, User.Role.ADMIN)
        self.assertTrue(approved_user.email_verified)
        self.assertTrue(approved_user.is_staff)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new-admin@example.com"])

    def test_admin_can_reject_pending_admin_registration_request(self):
        first_admin = self.create_admin_user()
        self.submit_admin_registration("reject-admin@example.com")
        mail.outbox.clear()
        self.verify_admin_registration("reject-admin@example.com")
        request = AdminRegistrationRequest.objects.get(email="reject-admin@example.com")
        mail.outbox.clear()

        self.client.force_authenticate(user=first_admin)
        rejection_response = self.client.patch(
            f"/api/adminpanel/admin-registration-requests/{request.id}/",
            {"status": "rejected"},
            format="json",
        )

        self.assertEqual(rejection_response.status_code, 200)
        request.refresh_from_db()
        self.assertEqual(request.status, AdminRegistrationRequest.Status.REJECTED)
        self.assertEqual(request.reviewed_by_id, first_admin.id)
        self.assertFalse(User.objects.filter(email="reject-admin@example.com").exists())
        self.assertEqual(len(mail.outbox), 0)
