from django.db import models

from apps.common.models import UUIDPrimaryKeyModel
from apps.companies.models import CompanyProfile


class Interest(UUIDPrimaryKeyModel):
    class Status(models.TextChoices):
        EXPRESSED = "expressed", "Expressed"
        CONTACTED = "contacted", "Contacted"
        ARCHIVED = "archived", "Archived"

    corper = models.ForeignKey(
        "corpers.CorperProfile", on_delete=models.CASCADE, related_name="interests"
    )
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="interested_corpers")
    message = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EXPRESSED)
    corper_expressed_at = models.DateTimeField(null=True, blank=True)
    company_expressed_at = models.DateTimeField(null=True, blank=True)
    viewed_by_company_at = models.DateTimeField(null=True, blank=True)
    viewed_by_corper_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["corper", "company"], name="unique_interest_pair")
        ]
