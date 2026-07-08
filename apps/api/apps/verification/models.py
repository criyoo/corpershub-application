from django.conf import settings
from django.db import models
from django.utils.dateparse import parse_date

from apps.common.models import UUIDPrimaryKeyModel
from apps.corpers.models import CorperProfile


class VerificationAttempt(UUIDPrimaryKeyModel):
    class VerificationType(models.TextChoices):
        BIODATA = "biodata", "Biodata"
        NIN = "nin", "NIN"
        CALLUP = "callup", "NYSC Call-up"
        STATE_CODE = "state_code", "NYSC State Code"
        PROFILE = "profile", "Profile"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    corper = models.ForeignKey("corpers.CorperProfile", on_delete=models.CASCADE, related_name="verification_attempts")
    verification_type = models.CharField(max_length=20, choices=VerificationType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_value_masked = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verification_reviews",
    )
    review_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["verification_type", "status"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_corper_status()

    def _sync_corper_status(self):
        if self.status == self.Status.FAILED:
            return

        corper = self.corper
        corper_model = type(corper)
        fields_to_update = ["updated_at"]

        if self.verification_type == self.VerificationType.PROFILE:
            if self.status == self.Status.APPROVED:
                corper.verification_status = corper_model.VerificationStatus.VERIFIED
            elif self.status == self.Status.REJECTED:
                corper.verification_status = corper_model.VerificationStatus.REJECTED
            else:
                corper.verification_status = corper_model.VerificationStatus.UNDER_REVIEW
            fields_to_update.append("verification_status")
        elif self.verification_type == self.VerificationType.NIN:
            if self.status == self.Status.APPROVED:
                corper.nin_verification_status = corper_model.SensitiveStatus.VERIFIED
                corper.biodata_verification_status = corper_model.SensitiveStatus.VERIFIED
            elif self.status == self.Status.REJECTED:
                corper.nin_verification_status = corper_model.SensitiveStatus.REJECTED
            else:
                corper.nin_verification_status = corper_model.SensitiveStatus.PENDING
            fields_to_update.append("nin_verification_status")
            if self.status == self.Status.APPROVED:
                fields_to_update.append("biodata_verification_status")
        elif self.verification_type == self.VerificationType.BIODATA:
            if self.status == self.Status.APPROVED:
                corper.biodata_verification_status = corper_model.SensitiveStatus.VERIFIED
                biodata = self.metadata or {}
                corper.full_name = str(biodata.get("full_name", "")).strip()
                corper.first_name = str(biodata.get("first_name", "")).strip()
                corper.middle_name = str(biodata.get("middle_name", "")).strip()
                corper.surname = str(biodata.get("surname", "")).strip()
                corper.date_of_birth = parse_date(str(biodata.get("date_of_birth", "")).strip()) or None
                corper.gender = str(biodata.get("gender", "")).strip().lower()
                corper.mobile_number = str(biodata.get("mobile_number", "")).strip()
                corper.state_of_origin = str(biodata.get("state_of_origin", "")).strip()
                corper.country_of_birth = str(biodata.get("country_of_birth", "")).strip()
                corper.university_matriculation_number = str(biodata.get("university_matriculation_number", "")).strip()
                fields_to_update.extend(
                    [
                        "full_name",
                        "first_name",
                        "middle_name",
                        "surname",
                        "date_of_birth",
                        "gender",
                        "mobile_number",
                        "state_of_origin",
                        "country_of_birth",
                        "university_matriculation_number",
                    ]
                )
            elif self.status == self.Status.REJECTED:
                corper.biodata_verification_status = corper_model.SensitiveStatus.REJECTED
            else:
                corper.biodata_verification_status = corper_model.SensitiveStatus.PENDING
            fields_to_update.append("biodata_verification_status")
        elif self.verification_type == self.VerificationType.CALLUP:
            if self.status == self.Status.APPROVED:
                corper.nysc_callup_verification_status = corper_model.SensitiveStatus.VERIFIED
            elif self.status == self.Status.REJECTED:
                corper.nysc_callup_verification_status = corper_model.SensitiveStatus.REJECTED
            else:
                corper.nysc_callup_verification_status = corper_model.SensitiveStatus.PENDING
            fields_to_update.append("nysc_callup_verification_status")
        elif self.verification_type == self.VerificationType.STATE_CODE:
            if self.status == self.Status.APPROVED:
                corper.nysc_state_code_verification_status = corper_model.SensitiveStatus.VERIFIED
            elif self.status == self.Status.REJECTED:
                corper.nysc_state_code_verification_status = corper_model.SensitiveStatus.REJECTED
            else:
                corper.nysc_state_code_verification_status = corper_model.SensitiveStatus.PENDING
            fields_to_update.append("nysc_state_code_verification_status")

        corper.save(update_fields=fields_to_update, skip_attempt_sync=True)


class CorperVerification(CorperProfile):
    class Meta:
        proxy = True
        verbose_name = "Verification"
        verbose_name_plural = "Verifications"


class BaseDikriptVerificationCache(UUIDPrimaryKeyModel):
    lookup_hash = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-updated_at"]


class NINDikriptVerificationCache(BaseDikriptVerificationCache):
    class Meta(BaseDikriptVerificationCache.Meta):
        db_table = "verification_nin_dikriptverificationcache"
        constraints = [
            models.UniqueConstraint(
                fields=["lookup_hash"],
                name="verification_unique_nin_dikript_lookup_cache",
            )
        ]


class CACDikriptVerificationCache(BaseDikriptVerificationCache):
    class Meta(BaseDikriptVerificationCache.Meta):
        db_table = "verification_cac_dikriptverificationcache"
        constraints = [
            models.UniqueConstraint(
                fields=["lookup_hash"],
                name="verification_unique_cac_dikript_lookup_cache",
            )
        ]


class DikriptVerificationCache:
    class VerificationType(models.TextChoices):
        NIN = "nin", "NIN"
        CAC = "cac", "CAC"

    @classmethod
    def get_model(cls, verification_type: str):
        if verification_type == cls.VerificationType.NIN:
            return NINDikriptVerificationCache
        if verification_type == cls.VerificationType.CAC:
            return CACDikriptVerificationCache
        raise ValueError(f"Unsupported Dikript verification type: {verification_type}")
