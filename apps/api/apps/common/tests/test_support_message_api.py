from django.core import mail
from rest_framework.test import APITestCase

from apps.accounts.models import User


class SupportMessageAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="member@example.com",
            password="ComplexPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        self.client.force_authenticate(self.user)

    def test_support_message_sends_support_email(self):
        response = self.client.post(
            "/api/common/support-messages/",
            {
                "kind": "support",
                "topic": "Technical issues",
                "message": "The page is not loading properly.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Message sent successfully.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["support@corpershub.ng"])
        self.assertEqual(mail.outbox[0].subject, "Support topic - Technical issues")
        self.assertIn("The page is not loading properly.", mail.outbox[0].body)

    def test_support_message_sends_product_feedback_email(self):
        response = self.client.post(
            "/api/common/support-messages/",
            {
                "kind": "improvement",
                "title": "Better notifications",
                "message": "Please add clearer read indicators.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["products@corpershub.ng"])
        self.assertEqual(
            mail.outbox[0].subject,
            "Product Improvement Suggestions - Better notifications",
        )
