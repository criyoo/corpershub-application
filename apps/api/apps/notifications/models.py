from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class Notification(UUIDPrimaryKeyModel):
    class Type(models.TextChoices):
        EMAIL_VERIFICATION_SUCCESS = "email_verification_success", "Email Verification Success"
        EMAIL_VERIFICATION_FAILURE = "email_verification_failure", "Email Verification Failure"
        PROFILE_VERIFICATION_UPDATE = "profile_verification_update", "Profile Verification Update"
        CORPER_INTEREST_RECEIVED = "corper_interest_received", "Corper Interest Received"
        NEW_CHAT_MESSAGE = "new_chat_message", "New Chat Message"
        PAYMENT_SUCCESS = "payment_success", "Payment Success"
        PAYMENT_FAILURE = "payment_failure", "Payment Failure"
        SUBSCRIPTION_EXPIRING = "subscription_expiring", "Subscription Expiring"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(max_length=64, choices=Type.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at"])]
