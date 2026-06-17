from django.conf import settings
from django.db import models
from django.db.models import Q
import hashlib

from apps.common.fields import EncryptedCharField
from apps.common.legal import CORPER_LEGAL_DOCUMENT_SLUGS, has_accepted_all_required_legal_documents
from apps.common.models import UUIDPrimaryKeyModel
from apps.common.utils import calculate_age, mask_identifier
from apps.common.validators import (
    normalize_mobile_number,
    normalize_nigerian_mobile_number_to_international,
    normalize_nin_number,
    normalize_nysc_callup_number,
    normalize_nysc_state_code,
    normalize_university_matriculation_number,
)


def hash_sensitive_identifier(value: str | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


class CorperProfile(UUIDPrimaryKeyModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class ApprovalStatus(models.TextChoices):
        UNSUBMITTED = "unsubmitted", "Unsubmitted"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"

    class Batch(models.TextChoices):
        BATCH_A = "Batch A", "Batch A"
        BATCH_B = "Batch B", "Batch B"
        BATCH_C = "Batch C", "Batch C"

    class Stream(models.TextChoices):
        STREAM_1 = "Stream 1", "Stream 1"
        STREAM_2 = "Stream 2", "Stream 2"

    class SensitiveStatus(models.TextChoices):
        UNSUBMITTED = "unsubmitted", "Unsubmitted"
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="corper_profile"
    )
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=120, blank=True, default="")
    middle_name = models.CharField(max_length=120, blank=True, default="")
    surname = models.CharField(max_length=120, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, blank=True, default="")
    state_of_origin = models.CharField(max_length=120, blank=True, default="")
    country_of_birth = models.CharField(max_length=120, blank=True, default="")
    posting_location_state = models.CharField(max_length=120)
    batch = models.CharField(max_length=20, choices=Batch.choices, blank=True, default="")
    stream = models.CharField(max_length=20, choices=Stream.choices, blank=True, default="")
    field_of_study = models.CharField(max_length=255)
    degree = models.CharField(max_length=120)
    university = models.CharField(max_length=255)
    university_matriculation_number = models.CharField(max_length=120, blank=True, default="")
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    profile_photo = models.FileField(upload_to="corpers/profile-photos/", null=True, blank=True)
    nin_number = EncryptedCharField(blank=True)
    nin_last4 = models.CharField(max_length=4, blank=True)
    nin_lookup_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    mobile_number = models.CharField(max_length=20)
    nysc_callup_number = models.CharField(max_length=120)
    nysc_callup_document = models.FileField(
        upload_to="corpers/verification-documents/callup/",
        null=True,
        blank=True,
    )
    nysc_callup_lookup_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    nysc_state_code = models.CharField(max_length=120, blank=True, default="")
    nysc_state_code_document = models.FileField(
        upload_to="corpers/verification-documents/state-code/",
        null=True,
        blank=True,
    )
    nysc_state_code_lookup_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    skill = models.CharField(max_length=255)
    technical_skills = models.CharField(max_length=255, blank=True, default="")
    soft_skills = models.CharField(max_length=255, blank=True, default="")
    languages_spoken = models.CharField(max_length=255, blank=True, default="")
    available_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    preferred_sector = models.CharField(max_length=120, blank=True, default="")
    preferred_organization_type = models.CharField(max_length=120, blank=True, default="")
    preferred_placement_type = models.CharField(max_length=120, blank=True, default="")
    preferred_monthly_allowance = models.CharField(max_length=120, blank=True, default="")
    preferred_organization_experience = models.TextField(blank=True)
    terms_of_agreement_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_of_use_accepted_at = models.DateTimeField(null=True, blank=True)
    legal_acceptances = models.JSONField(default=dict, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    biodata_verification_status = models.CharField(
        max_length=20, choices=SensitiveStatus.choices, default=SensitiveStatus.UNSUBMITTED
    )
    nin_verification_status = models.CharField(
        max_length=20, choices=SensitiveStatus.choices, default=SensitiveStatus.UNSUBMITTED
    )
    nysc_callup_verification_status = models.CharField(
        max_length=20, choices=SensitiveStatus.choices, default=SensitiveStatus.UNSUBMITTED
    )
    nysc_state_code_verification_status = models.CharField(
        max_length=20, choices=SensitiveStatus.choices, default=SensitiveStatus.UNSUBMITTED
    )
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.UNSUBMITTED
    )
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True)
    directory_visibility_paused = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Corper profile"
        verbose_name_plural = "Corpers profiles"
        indexes = [
            models.Index(fields=["posting_location_state"]),
            models.Index(fields=["field_of_study", "degree"]),
            models.Index(fields=["university", "graduation_year"]),
            models.Index(fields=["skill"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["university_matriculation_number"],
                condition=~Q(university_matriculation_number=""),
                name="corpers_unique_matric_number",
            ),
            models.UniqueConstraint(
                fields=["mobile_number"],
                condition=~Q(mobile_number=""),
                name="corpers_unique_mobile_number",
            ),
            models.UniqueConstraint(
                fields=["nin_lookup_hash"],
                condition=~Q(nin_lookup_hash=""),
                name="corpers_unique_nin_hash",
            ),
            models.UniqueConstraint(
                fields=["nysc_callup_lookup_hash"],
                condition=~Q(nysc_callup_lookup_hash=""),
                name="corpers_unique_callup_hash",
            ),
            models.UniqueConstraint(
                fields=["nysc_state_code_lookup_hash"],
                condition=~Q(nysc_state_code_lookup_hash=""),
                name="corpers_unique_state_code_hash",
            ),
        ]

    @classmethod
    def has_university_matriculation_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_university_matriculation_number(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(university_matriculation_number=normalized_value)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def has_mobile_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_nigerian_mobile_number_to_international(value)
        if not normalized_value:
            return False
        candidates = {normalized_value}
        raw_value = str(value or "").strip()
        if raw_value:
            candidates.add(normalize_mobile_number(raw_value))
        if normalized_value.startswith("+234"):
            candidates.add(f"0{normalized_value[4:]}")
            candidates.add(normalized_value[1:])
        queryset = cls.objects.filter(mobile_number__in=list(candidates))
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def has_nin_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_nin_number(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(nin_lookup_hash=hash_sensitive_identifier(normalized_value))
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def has_nysc_callup_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_nysc_callup_number(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(nysc_callup_lookup_hash=hash_sensitive_identifier(normalized_value))
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def has_nysc_state_code(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_nysc_state_code(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(nysc_state_code_lookup_hash=hash_sensitive_identifier(normalized_value))
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def discoverable_q(cls) -> Q:
        return (
            Q(directory_visibility_paused=False)
            & ~Q(full_name="")
            & Q(date_of_birth__isnull=False)
            & ~Q(posting_location_state="")
            & ~Q(batch="")
            & ~Q(stream="")
            & ~Q(field_of_study="")
            & ~Q(degree="")
            & ~Q(university="")
            & Q(graduation_year__isnull=False)
            & Q(profile_photo__isnull=False)
            & ~Q(profile_photo="")
            & ~Q(mobile_number="")
            & ~Q(nysc_callup_number="")
            & ~Q(nysc_state_code="")
            & ~Q(skill="")
            & ~Q(technical_skills="")
            & ~Q(soft_skills="")
            & ~Q(languages_spoken="")
            & Q(available_date__isnull=False)
            & ~Q(bio="")
            & Q(terms_of_agreement_accepted_at__isnull=False)
            & Q(terms_of_use_accepted_at__isnull=False)
        )

    @classmethod
    def directory_visibility_q(cls) -> Q:
        return (
            cls.discoverable_q()
            & Q(approval_status=cls.ApprovalStatus.APPROVED)
            & Q(nin_verification_status=cls.SensitiveStatus.VERIFIED)
            & Q(nysc_callup_verification_status=cls.SensitiveStatus.VERIFIED)
            & Q(nysc_state_code_verification_status=cls.SensitiveStatus.VERIFIED)
            & Q(date_of_birth__isnull=False)
            & Q(graduation_year__isnull=False)
            & Q(profile_photo__isnull=False)
            & ~Q(profile_photo="")
            & ~Q(posting_location_state="")
            & ~Q(field_of_study="")
            & ~Q(degree="")
            & ~Q(university="")
            & ~Q(mobile_number="")
            & ~Q(skill="")
            & ~Q(technical_skills="")
            & ~Q(soft_skills="")
            & ~Q(languages_spoken="")
            & Q(available_date__isnull=False)
            & ~Q(bio="")
        )

    @property
    def age(self):
        return calculate_age(self.date_of_birth)

    @property
    def masked_nin_number(self):
        if not self.nin_last4:
            return ""
        return f"******{self.nin_last4}"

    @property
    def masked_callup_number(self):
        value = self.nysc_callup_number or ""
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

    @property
    def masked_state_code(self):
        return mask_identifier(self.nysc_state_code, prefix=4, suffix=2)

    @property
    def masked_university_matriculation_number(self):
        return mask_identifier(self.university_matriculation_number, prefix=2, suffix=2)

    @property
    def documents_verified(self) -> bool:
        return (
            self.biodata_verification_status == self.SensitiveStatus.VERIFIED
            and self.nin_verification_status == self.SensitiveStatus.VERIFIED
            and self.nysc_callup_verification_status == self.SensitiveStatus.VERIFIED
            and self.nysc_state_code_verification_status == self.SensitiveStatus.VERIFIED
        )

    @property
    def derived_verification_status(self) -> str:
        if self.documents_verified:
            return self.VerificationStatus.VERIFIED
        if (
            self.biodata_verification_status == self.SensitiveStatus.REJECTED
            or self.nin_verification_status == self.SensitiveStatus.REJECTED
            or self.nysc_callup_verification_status == self.SensitiveStatus.REJECTED
            or self.nysc_state_code_verification_status == self.SensitiveStatus.REJECTED
        ):
            return self.VerificationStatus.REJECTED
        return self.VerificationStatus.PENDING

    @property
    def onboarding_complete(self) -> bool:
        return self.documents_verified and self.is_complete

    @property
    def next_profile_path(self) -> str:
        if not self.documents_verified:
            return "/corper/verification"
        if self.profile_fields_complete and not self.terms_accepted:
            return "/corper/profile/terms"
        return "/corper/profile"

    @property
    def profile_locked(self) -> bool:
        return self.documents_verified and self.is_complete

    @property
    def profile_fields_complete(self) -> bool:
        required_values = (
            self.full_name,
            self.date_of_birth,
            self.posting_location_state,
            self.batch,
            self.stream,
            self.field_of_study,
            self.degree,
            self.university,
            self.graduation_year,
            self.profile_photo,
            self.mobile_number,
            self.nysc_callup_number,
            self.nysc_state_code,
            self.skill,
            self.technical_skills,
            self.soft_skills,
            self.languages_spoken,
            self.available_date,
            self.bio,
        )
        return all(bool(value and str(value).strip()) for value in required_values)

    @property
    def terms_accepted(self) -> bool:
        if self.legal_acceptances:
            return has_accepted_all_required_legal_documents(
                self.legal_acceptances, CORPER_LEGAL_DOCUMENT_SLUGS
            )
        return bool(self.terms_of_agreement_accepted_at and self.terms_of_use_accepted_at)

    @property
    def is_complete(self) -> bool:
        return self.profile_fields_complete and self.terms_accepted

    def save(self, *args, **kwargs):
        skip_attempt_sync = kwargs.pop("skip_attempt_sync", False)
        update_fields = kwargs.get("update_fields")
        update_fields_set = set(update_fields) if update_fields is not None else None
        previous_statuses = None
        if self.pk and not skip_attempt_sync:
            previous_statuses = type(self).objects.filter(pk=self.pk).values(
                "verification_status",
                "biodata_verification_status",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
            ).first()
        self.first_name = " ".join(str(self.first_name or "").split())
        self.middle_name = " ".join(str(self.middle_name or "").split())
        self.surname = " ".join(str(self.surname or "").split())
        self.state_of_origin = " ".join(str(self.state_of_origin or "").split())
        self.country_of_birth = " ".join(str(self.country_of_birth or "").split())
        self.full_name = " ".join(str(self.full_name or "").split())
        if self.first_name or self.middle_name or self.surname:
            self.full_name = " ".join(
                part for part in (self.first_name, self.middle_name, self.surname) if part
            )
        elif self.full_name:
            name_parts = self.full_name.split()
            if name_parts:
                self.first_name = name_parts[0]
                self.surname = name_parts[-1] if len(name_parts) > 1 else ""
                self.middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
        self.university_matriculation_number = normalize_university_matriculation_number(
            self.university_matriculation_number
        )
        self.mobile_number = normalize_nigerian_mobile_number_to_international(self.mobile_number)
        self.nin_number = normalize_nin_number(self.nin_number)
        self.nysc_callup_number = normalize_nysc_callup_number(self.nysc_callup_number)
        self.nysc_state_code = normalize_nysc_state_code(self.nysc_state_code)
        self.verification_status = self.derived_verification_status
        if update_fields_set is not None:
            update_fields_set.add("verification_status")
        if self.nin_number:
            self.nin_last4 = str(self.nin_number)[-4:]
            self.nin_lookup_hash = hash_sensitive_identifier(self.nin_number)
            if update_fields_set is not None and "nin_number" in update_fields_set:
                update_fields_set.add("nin_last4")
                update_fields_set.add("nin_lookup_hash")
        else:
            self.nin_last4 = ""
            self.nin_lookup_hash = ""
            if update_fields_set is not None and "nin_number" in update_fields_set:
                update_fields_set.add("nin_last4")
                update_fields_set.add("nin_lookup_hash")
        if self.nysc_callup_number:
            self.nysc_callup_lookup_hash = hash_sensitive_identifier(self.nysc_callup_number)
            if update_fields_set is not None and "nysc_callup_number" in update_fields_set:
                update_fields_set.add("nysc_callup_lookup_hash")
        else:
            self.nysc_callup_lookup_hash = ""
            if update_fields_set is not None and "nysc_callup_number" in update_fields_set:
                update_fields_set.add("nysc_callup_lookup_hash")
        if self.nysc_state_code:
            self.nysc_state_code_lookup_hash = hash_sensitive_identifier(self.nysc_state_code)
            if update_fields_set is not None and "nysc_state_code" in update_fields_set:
                update_fields_set.add("nysc_state_code_lookup_hash")
        else:
            self.nysc_state_code_lookup_hash = ""
            if update_fields_set is not None and "nysc_state_code" in update_fields_set:
                update_fields_set.add("nysc_state_code_lookup_hash")
        if update_fields_set is not None:
            kwargs["update_fields"] = list(update_fields_set)
        super().save(*args, **kwargs)
        if not skip_attempt_sync:
            self._sync_verification_attempts(previous_statuses)

    def _sync_verification_attempts(self, previous_statuses=None):
        status_mappings = (
            (
                "verification_status",
                "profile",
                {
                    self.VerificationStatus.PENDING: "pending",
                    self.VerificationStatus.UNDER_REVIEW: "pending",
                    self.VerificationStatus.VERIFIED: "approved",
                    self.VerificationStatus.REJECTED: "rejected",
                },
            ),
            (
                "biodata_verification_status",
                "biodata",
                {
                    self.SensitiveStatus.PENDING: "pending",
                    self.SensitiveStatus.VERIFIED: "approved",
                    self.SensitiveStatus.REJECTED: "rejected",
                },
            ),
            (
                "nin_verification_status",
                "nin",
                {
                    self.SensitiveStatus.PENDING: "pending",
                    self.SensitiveStatus.VERIFIED: "approved",
                    self.SensitiveStatus.REJECTED: "rejected",
                },
            ),
            (
                "nysc_callup_verification_status",
                "callup",
                {
                    self.SensitiveStatus.PENDING: "pending",
                    self.SensitiveStatus.VERIFIED: "approved",
                    self.SensitiveStatus.REJECTED: "rejected",
                },
            ),
            (
                "nysc_state_code_verification_status",
                "state_code",
                {
                    self.SensitiveStatus.PENDING: "pending",
                    self.SensitiveStatus.VERIFIED: "approved",
                    self.SensitiveStatus.REJECTED: "rejected",
                },
            ),
        )

        for field_name, verification_type, mapping in status_mappings:
            if previous_statuses and previous_statuses.get(field_name) == getattr(self, field_name):
                continue

            next_status = mapping.get(getattr(self, field_name))
            if not next_status:
                continue

            latest_attempt = (
                self.verification_attempts.filter(verification_type=verification_type)
                .exclude(status="failed")
                .order_by("-created_at")
                .first()
            )
            if latest_attempt is None or latest_attempt.status == next_status:
                continue

            latest_attempt.status = next_status
            latest_attempt.save(update_fields=["status", "updated_at"])

    def __str__(self) -> str:
        return self.full_name
