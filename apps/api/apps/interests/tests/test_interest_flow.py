from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.companies.services import ensure_company_profile
from apps.interests.models import Interest
from apps.notifications.models import Notification
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end, ensure_trial_subscription
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


class InterestFlowTests(APITestCase):
    def setUp(self):
        self.corper_user = User.objects.create_user(
            email="corper@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.corper = ensure_corper_profile(self.corper_user)

        self.company_user = User.objects.create_user(
            email="talent@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.company = ensure_company_profile(self.company_user)
        self.company.company_location_state = "Lagos"
        self.company.company_location_city = "Yaba"
        self.company.company_sector = "Tech"
        self.company.company_function = "Support"
        self.company.desired_corper_description = "Looking for NYSC support talent."
        self.company.save()

    def activate_paid_corper_plan(self):
        plan = SubscriptionPlan.objects.get(code=six)
        starts_at = timezone.now()
        ends_at = calculate_subscription_end(plan=plan, starts_at=starts_at)
        UserSubscription.objects.create(
            user=self.corper_user,
            plan=plan,
            status=UserSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
            metadata={"source": "test"},
        )

    def test_express_interest_creates_notification_for_company(self):
        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.corper_user)
        response = self.client.post(f"/api/interests/companies/{self.company.id}/express/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.company_user,
                notification_type=Notification.Type.CORPER_INTEREST_RECEIVED,
            ).exists()
        )

    def test_free_trial_corper_cannot_express_interest(self):
        ensure_trial_subscription(user=self.corper_user)

        self.client.force_authenticate(self.corper_user)
        response = self.client.post(f"/api/interests/companies/{self.company.id}/express/", {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertIn("paid plans only", str(response.data["detail"]).lower())

    def test_corper_can_view_companies_they_showed_interest_in(self):
        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.corper_user)
        self.client.post(f"/api/interests/companies/{self.company.id}/express/", {}, format="json")

        response = self.client.get("/api/interests/mine/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["company"]["company_name"], self.company.company_name)
        self.assertIsNotNone(response.data["results"][0]["corper_expressed_at"])

    def test_company_can_save_corper_to_interest(self):
        self.corper.full_name = "Ada Corper"
        self.corper.save(update_fields=["full_name", "updated_at"])

        self.client.force_authenticate(self.company_user)
        response = self.client.post(f"/api/interests/corpers/{self.corper.id}/express/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "Corper added to Interest.")
        interest = Interest.objects.get(corper=self.corper, company=self.company)
        self.assertIsNotNone(interest.company_expressed_at)

        saved_response = self.client.get("/api/interests/saved/")
        self.assertEqual(saved_response.status_code, 200)
        self.assertEqual(saved_response.data["results"][0]["corper"]["full_name"], "Ada Corper")
        self.assertFalse(saved_response.data["results"][0]["corper_has_paid_access"])

    def test_corper_can_view_companies_interested_in_them(self):
        Interest.objects.create(
            corper=self.corper,
            company=self.company,
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/interests/companies/received/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["company"]["company_name"], self.company.company_name)
        self.assertIsNotNone(response.data["results"][0]["company_expressed_at"])

    def test_corper_received_company_interests_are_marked_viewed(self):
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/interests/companies/received/")

        self.assertEqual(response.status_code, 200)
        interest.refresh_from_db()
        self.assertIsNotNone(interest.viewed_by_corper_at)

    def test_unread_count_ignores_unrelated_notifications_for_corpers(self):
        Interest.objects.create(
            corper=self.corper,
            company=self.company,
            company_expressed_at=timezone.now(),
        )
        Notification.objects.create(
            recipient=self.corper_user,
            notification_type=Notification.Type.EMAIL_VERIFICATION_SUCCESS,
            title="Email verified",
            body="Your email is verified.",
        )
        Notification.objects.create(
            recipient=self.corper_user,
            notification_type=Notification.Type.NEW_CHAT_MESSAGE,
            title="New chat message",
            body="You have a new message.",
        )

        self.client.force_authenticate(self.corper_user)

        unread_response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(unread_response.status_code, 200)
        self.assertEqual(unread_response.data["count"], 1)
        self.assertEqual(unread_response.data["new_count"], 1)
        self.assertEqual(unread_response.data["unread_count"], 1)

        self.client.get("/api/interests/companies/received/")

        post_read_response = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(post_read_response.status_code, 200)
        self.assertEqual(post_read_response.data["count"], 1)
        self.assertEqual(post_read_response.data["new_count"], 0)
        self.assertEqual(post_read_response.data["unread_count"], 0)

    def test_unread_count_for_company_only_counts_unread_corper_interest_notifications(self):
        Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )
        Notification.objects.create(
            recipient=self.company_user,
            notification_type=Notification.Type.CORPER_INTEREST_RECEIVED,
            title="New corper interest received",
            body="Ada Corper has indicated interest in your listing.",
        )
        Notification.objects.create(
            recipient=self.company_user,
            notification_type=Notification.Type.EMAIL_VERIFICATION_SUCCESS,
            title="Email verified",
            body="Your email is verified.",
        )
        Notification.objects.create(
            recipient=self.company_user,
            notification_type=Notification.Type.NEW_CHAT_MESSAGE,
            title="New chat message",
            body="You have a new message.",
        )

        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/notifications/unread-count/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["new_count"], 1)
        self.assertEqual(response.data["unread_count"], 1)
