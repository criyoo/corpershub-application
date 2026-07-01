from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.subscriptions.models import SubscriptionPlan, UserSubscription

from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


FREE_PLAN_CODE = "free"
CORPER_QUARTERLY_PLAN_CODE = three
CORPER_SEMIANNUAL_PLAN_CODE = six
CORPER_YEARLY_PLAN_CODE = twelve
TRIAL_DURATION_DAYS = 7
PAID_DURATION_MONTHS = 6
CORPER_PAID_ACCESS_REQUIRED_MESSAGE = "This feature is available on paid plans only. Subscribe to continue."
CORPER_PLAN_RANKS = {
    FREE_PLAN_CODE: 0,
    CORPER_QUARTERLY_PLAN_CODE: 1,
    CORPER_SEMIANNUAL_PLAN_CODE: 2,
    CORPER_YEARLY_PLAN_CODE: 3,
}


@dataclass(frozen=True)
class SubscriptionTransition:
    amount_kobo: int
    effective_starts_at: object
    previous_subscription: UserSubscription | None
    is_upgrade: bool


def user_supports_subscriptions(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and getattr(user, "role", "") == User.Role.CORPER)


def add_months(value, months: int):
    month_index = value.month - 1 + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def calculate_subscription_end(*, plan: SubscriptionPlan, starts_at):
    interval_map = {
        SubscriptionPlan.BillingInterval.TRIAL: lambda value: value + timedelta(days=TRIAL_DURATION_DAYS),
        SubscriptionPlan.BillingInterval.SEMIANNUAL: lambda value: add_months(value, PAID_DURATION_MONTHS),
        SubscriptionPlan.BillingInterval.MONTHLY: lambda value: add_months(value, 1),
        SubscriptionPlan.BillingInterval.QUARTERLY: lambda value: add_months(value, 3),
        SubscriptionPlan.BillingInterval.YEARLY: lambda value: add_months(value, 12),
    }
    try:
        return interval_map[plan.billing_interval](starts_at)
    except KeyError as exc:
        raise ValueError("Unsupported billing interval.") from exc


def get_corper_plan_rank(plan: SubscriptionPlan) -> int | None:
    return CORPER_PLAN_RANKS.get(plan.code)


def _get_latest_paid_subscription(*, user) -> UserSubscription | None:
    return (
        UserSubscription.objects.select_related("plan")
        .filter(user=user, plan__price_kobo__gt=0)
        .exclude(status=UserSubscription.Status.PAST_DUE)
        .order_by("-created_at")
        .first()
    )


def get_corper_plan_transition(*, user, plan: SubscriptionPlan, now=None) -> SubscriptionTransition:
    if not user_supports_subscriptions(user):
        raise PermissionDenied("Only corper accounts can start a subscription.")

    current_time = now or timezone.now()
    refresh_user_subscriptions(user=user, now=current_time)

    if get_corper_plan_rank(plan) is None:
        raise PermissionDenied("This plan is not available for corper billing.")

    if plan.price_kobo == 0:
        if UserSubscription.objects.filter(user=user).exists():
            raise PermissionDenied("The 7-day free trial can only be started once per corper account.")
        return SubscriptionTransition(
            amount_kobo=0,
            effective_starts_at=current_time,
            previous_subscription=None,
            is_upgrade=False,
        )

    current_subscription = get_current_browse_subscription(user=user, autocreate=False, now=current_time)
    return SubscriptionTransition(
        amount_kobo=plan.price_kobo,
        effective_starts_at=current_time,
        previous_subscription=current_subscription,
        is_upgrade=False,
    )


def get_free_plan() -> SubscriptionPlan:
    plan, _ = SubscriptionPlan.objects.get_or_create(
        code=FREE_PLAN_CODE,
        defaults={
            "name": "7 Days Free Trial",
            "description": "Browse companies for 7 days before moving to a paid corper plan.",
            "price_kobo": 0,
            "currency": "NGN",
            "billing_interval": SubscriptionPlan.BillingInterval.TRIAL,
            "applies_to": SubscriptionPlan.AppliesTo.CORPER,
            "features": [
                "Browse companies",
                "Dashboard access",
                "Notifications",
            ],
            "is_active": True,
        },
    )
    return plan


def get_paid_plan_code_for_role(role: str) -> str:
    if role == User.Role.CORPER:
        return CORPER_SEMIANNUAL_PLAN_CODE
    raise ValueError("Unsupported role for paid subscription.")


def get_corper_signup_plan(plan_code: str) -> SubscriptionPlan:
    plan = (
        SubscriptionPlan.objects.filter(code=plan_code, is_active=True)
        .filter(applies_to=SubscriptionPlan.AppliesTo.CORPER)
        .first()
    )
    if plan is None:
        raise ValueError("Unsupported corper subscription plan.")
    return plan


def refresh_user_subscriptions(*, user, now=None) -> None:
    if not user_supports_subscriptions(user):
        return
    current_time = now or timezone.now()
    UserSubscription.objects.filter(
        user=user,
        status__in=[
            UserSubscription.Status.TRIAL,
            UserSubscription.Status.ACTIVE,
            UserSubscription.Status.CANCELLED,
        ],
        ends_at__isnull=False,
        ends_at__lte=current_time,
    ).update(
        status=UserSubscription.Status.EXPIRED,
        next_billing_at=None,
        updated_at=current_time,
    )


def ensure_trial_subscription(
    *, user, now=None, plan: SubscriptionPlan | None = None, metadata_source="default-trial"
) -> UserSubscription | None:
    if not user_supports_subscriptions(user):
        return None

    with transaction.atomic():
        if UserSubscription.objects.select_for_update().filter(user=user).exists():
            refresh_user_subscriptions(user=user, now=now)
            return get_current_browse_subscription(user=user, autocreate=False, now=now)

        current_time = now or timezone.now()
        plan = plan or get_free_plan()
        ends_at = calculate_subscription_end(plan=plan, starts_at=current_time)
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status=UserSubscription.Status.TRIAL,
            starts_at=current_time,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
            metadata={"source": metadata_source},
        )
        return subscription


def list_user_subscriptions(*, user):
    if user_supports_subscriptions(user):
        refresh_user_subscriptions(user=user)
    return UserSubscription.objects.select_related("plan").filter(user=user)


def get_current_browse_subscription(*, user, autocreate=True, now=None) -> UserSubscription | None:
    if not user_supports_subscriptions(user):
        return None

    refresh_user_subscriptions(user=user, now=now)

    subscriptions = list(UserSubscription.objects.select_related("plan").filter(user=user))
    for status in (
        UserSubscription.Status.ACTIVE,
        UserSubscription.Status.TRIAL,
        UserSubscription.Status.CANCELLED,
    ):
        for subscription in subscriptions:
            if subscription.status == status:
                return subscription

    return None


def get_current_paid_subscription(*, user, now=None) -> UserSubscription | None:
    if not user_supports_subscriptions(user):
        return None
    refresh_user_subscriptions(user=user, now=now)
    return (
        UserSubscription.objects.select_related("plan")
        .filter(
            user=user,
            status__in=[UserSubscription.Status.ACTIVE, UserSubscription.Status.CANCELLED],
            plan__price_kobo__gt=0,
        )
        .order_by("-created_at")
        .first()
    )


def corper_has_paid_access(*, user, now=None) -> bool:
    if not getattr(user, "is_authenticated", False) or getattr(user, "role", "") != User.Role.CORPER:
        return False
    return get_current_paid_subscription(user=user, now=now) is not None


def enforce_corper_paid_access(*, user) -> UserSubscription:
    subscription = get_current_paid_subscription(user=user)
    if subscription is not None:
        return subscription
    raise PermissionDenied(CORPER_PAID_ACCESS_REQUIRED_MESSAGE)


def get_latest_subscription(*, user, autocreate=True, now=None) -> UserSubscription | None:
    current_subscription = get_current_browse_subscription(user=user, autocreate=autocreate, now=now)
    if current_subscription is not None:
        return current_subscription
    latest_subscription = (
        UserSubscription.objects.select_related("plan").filter(user=user).order_by("-created_at").first()
    )
    return latest_subscription


def activate_paid_subscription(*, subscription: UserSubscription, starts_at=None) -> UserSubscription:
    starts_at = starts_at or timezone.now()
    UserSubscription.objects.filter(
        user=subscription.user,
        status__in=[
            UserSubscription.Status.TRIAL,
            UserSubscription.Status.ACTIVE,
            UserSubscription.Status.CANCELLED,
        ],
    ).exclude(pk=subscription.pk).update(
        status=UserSubscription.Status.EXPIRED,
        next_billing_at=None,
        updated_at=starts_at,
    )
    subscription.status = UserSubscription.Status.ACTIVE
    subscription.starts_at = starts_at
    subscription.ends_at = calculate_subscription_end(plan=subscription.plan, starts_at=starts_at)
    subscription.next_billing_at = subscription.ends_at
    subscription.is_auto_renew = False
    subscription.save(
        update_fields=[
            "status",
            "starts_at",
            "ends_at",
            "next_billing_at",
            "is_auto_renew",
            "updated_at",
        ]
    )
    return subscription


def enforce_browse_access(*, user) -> UserSubscription | None:
    if not user_supports_subscriptions(user):
        return None
    current_subscription = get_current_browse_subscription(user=user, autocreate=True)
    if current_subscription is not None:
        return current_subscription
    latest_subscription = (
        UserSubscription.objects.select_related("plan").filter(user=user).order_by("-created_at").first()
    )
    if getattr(user, "role", "") == User.Role.CORPER:
        if latest_subscription is None:
            raise PermissionDenied("Choose a subscription plan on your billing page to start browsing.")
        if latest_subscription.status == UserSubscription.Status.PENDING:
            raise PermissionDenied("Your payment is pending. Browsing unlocks after it is confirmed.")
    raise PermissionDenied("Your 7-day free trial has expired. Upgrade to the Paid plan to continue browsing.")
