from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import (
    calculate_subscription_end,
    get_current_browse_subscription,
    get_current_paid_subscription,
    refresh_user_subscriptions,
)
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


class SubscriptionRulesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="subscriber@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.plan = SubscriptionPlan.objects.get(code=six)

    def test_cancelled_paid_plan_retains_access_until_expiry(self):
        starts_at = timezone.now() - timedelta(days=7)
        ends_at = calculate_subscription_end(plan=self.plan, starts_at=starts_at)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=UserSubscription.Status.CANCELLED,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
        )

        self.assertEqual(get_current_browse_subscription(user=self.user), subscription)
        self.assertEqual(get_current_paid_subscription(user=self.user), subscription)

    def test_cancelled_plan_expires_after_end_date(self):
        starts_at = timezone.now() - timedelta(days=200)
        ends_at = calculate_subscription_end(plan=self.plan, starts_at=starts_at)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=UserSubscription.Status.CANCELLED,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
        )

        refresh_user_subscriptions(user=self.user)

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, UserSubscription.Status.EXPIRED)
        self.assertIsNone(get_current_paid_subscription(user=self.user))
