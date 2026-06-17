from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class SubscriptionPlan(UUIDPrimaryKeyModel):
    class BillingInterval(models.TextChoices):
        TRIAL = "trial", "7 Days"
        SEMIANNUAL = "semiannual", "6 Months"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    class AppliesTo(models.TextChoices):
        COMPANY = "company", "Company"
        CORPER = "corper", "Corper"
        BOTH = "both", "Both"

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price_kobo = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="NGN")
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices)
    applies_to = models.CharField(max_length=20, choices=AppliesTo.choices, default=AppliesTo.COMPANY)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price_kobo", "name"]


class UserSubscription(UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    next_billing_at = models.DateTimeField(null=True, blank=True)
    is_auto_renew = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]
