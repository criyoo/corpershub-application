from django.conf import settings
from django.db import models

from apps.common.models import UUIDPrimaryKeyModel


class AuditLog(UUIDPrimaryKeyModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]
