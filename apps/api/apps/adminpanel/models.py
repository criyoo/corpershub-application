from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class PlatformOption(UUIDPrimaryKeyModel):
    class Category(models.TextChoices):
        SECTOR = "sector", "Sector"
        UNIVERSITY = "university", "University"
        DEGREE = "degree", "Degree"
        POSTING_LOCATION = "posting_location", "Posting Location"

    category = models.CharField(max_length=40, choices=Category.choices)
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "label"]
        constraints = [models.UniqueConstraint(fields=["category", "value"], name="unique_platform_option")]


class AdminRegistrationRequest(UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_admin_registration_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    approved_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_admin_registration_request",
    )

    class Meta:
        ordering = ["status", "-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"
