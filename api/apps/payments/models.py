from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class PaymentTransaction(UUIDPrimaryKeyModel):
    class Gateway(models.TextChoices):
        FLUTTERWAVE = "flutterwave", "Flutterwave"
        CARD = "card", "Card"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        ABANDONED = "abandoned", "Abandoned"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_transactions")
    subscription = models.ForeignKey(
        "subscriptions.UserSubscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    reference = models.CharField(max_length=120, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount_kobo = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    idempotency_key = models.CharField(max_length=120, unique=True)
    provider_payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["gateway", "status"])]


class PaymentWebhookEvent(UUIDPrimaryKeyModel):
    class ProcessStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    gateway = models.CharField(max_length=20)
    event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=120)
    signature = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    process_status = models.CharField(max_length=20, choices=ProcessStatus.choices, default=ProcessStatus.RECEIVED)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["gateway", "process_status"])]


class FlutterwavePaymentRecord(UUIDPrimaryKeyModel):
    internal_payment = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="flutterwave_record",
    )
    tx_ref = models.CharField(max_length=120, unique=True)
    flutterwave_transaction_id = models.CharField(max_length=120, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, default=PaymentTransaction.Status.PENDING)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "verified_at"])]
