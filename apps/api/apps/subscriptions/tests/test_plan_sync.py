from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans
from apps.subscriptions.models import SubscriptionPlan

free, three, six, twelve = billing_plans.keys()


class SyncSubscriptionPlansCommandTests(TestCase):
    def test_sync_subscription_plans_updates_existing_records(self):
        plan = SubscriptionPlan.objects.get(code=six)
        plan.price_kobo = 999
        plan.name = "Legacy 6 Months"
        plan.is_active = False
        plan.save(update_fields=["price_kobo", "name", "is_active", "updated_at"])

        retired_plan = SubscriptionPlan.objects.create(
            code="legacy-plan",
            name="Legacy",
            description="Legacy plan",
            price_kobo=12345,
            currency="NGN",
            billing_interval=SubscriptionPlan.BillingInterval.MONTHLY,
            applies_to=SubscriptionPlan.AppliesTo.CORPER,
            features=["Legacy access"],
            is_active=True,
        )

        stdout = StringIO()
        call_command("sync_subscription_plans", stdout=stdout)

        plan.refresh_from_db()
        retired_plan.refresh_from_db()

        self.assertEqual(plan.price_kobo, billing_plans[six])
        self.assertEqual(plan.name, "6 Months")
        self.assertTrue(plan.is_active)
        self.assertFalse(retired_plan.is_active)
        self.assertIn("Synchronized 4 subscription plans.", stdout.getvalue())
