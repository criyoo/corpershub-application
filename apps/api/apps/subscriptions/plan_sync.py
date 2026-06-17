from __future__ import annotations

from django.db import transaction

from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans
from apps.subscriptions.models import SubscriptionPlan

free, three, six, twelve = billing_plans.keys()


def build_default_subscription_plans() -> list[dict[str, object]]:
    return [
        {
            "code": free,
            "name": "7 Days Free Trial",
            "description": "Browse companies for 7 days before moving to a paid corper plan.",
            "price_kobo": billing_plans[free],
            "currency": "NGN",
            "billing_interval": SubscriptionPlan.BillingInterval.TRIAL,
            "applies_to": SubscriptionPlan.AppliesTo.CORPER,
            "features": ["7-day browsing access", "Dashboard access", "Notifications"],
            "is_active": True,
        },
        {
            "code": three,
            "name": "3 Months",
            "description": "One-off corper payment that unlocks full access for 3 months.",
            "price_kobo": billing_plans[three],
            "currency": "NGN",
            "billing_interval": SubscriptionPlan.BillingInterval.QUARTERLY,
            "applies_to": SubscriptionPlan.AppliesTo.CORPER,
            "features": [
                "3 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
        {
            "code": six,
            "name": "6 Months",
            "description": "One-off corper payment that unlocks full access for 6 months.",
            "price_kobo": billing_plans[six],
            "currency": "NGN",
            "billing_interval": SubscriptionPlan.BillingInterval.SEMIANNUAL,
            "applies_to": SubscriptionPlan.AppliesTo.CORPER,
            "features": [
                "6 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
        {
            "code": twelve,
            "name": "12 Months",
            "description": "One-off corper payment that unlocks full access for 12 months.",
            "price_kobo": billing_plans[twelve],
            "currency": "NGN",
            "billing_interval": SubscriptionPlan.BillingInterval.YEARLY,
            "applies_to": SubscriptionPlan.AppliesTo.CORPER,
            "features": [
                "12 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
    ]


def sync_subscription_plans(*, using: str = "default") -> int:
    plans = build_default_subscription_plans()
    plan_codes = [plan["code"] for plan in plans]
    queryset = SubscriptionPlan.objects.using(using)

    with transaction.atomic(using=using):
        for plan in plans:
            queryset.update_or_create(code=plan["code"], defaults=plan)
        queryset.exclude(code__in=plan_codes).update(is_active=False)

    return len(plans)
