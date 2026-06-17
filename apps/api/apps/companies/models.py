from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.legal import COMPANY_LEGAL_DOCUMENT_SLUGS, has_accepted_all_required_legal_documents
from apps.common.models import UUIDPrimaryKeyModel
from apps.companies.registration_lookup import normalize_company_registration_number
from apps.companies.validators import normalize_tax_identification_number


class CompanyProfile(UUIDPrimaryKeyModel):
    class VerificationStatus(models.TextChoices):
        UNSUBMITTED = "unsubmitted", "Unsubmitted"
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class ApprovalStatus(models.TextChoices):
        UNSUBMITTED = "unsubmitted", "Unsubmitted"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_profile"
    )
    company_name = models.CharField(max_length=255)
    company_registration_number = models.CharField(max_length=120)
    company_registration_date = models.DateField(null=True, blank=True)
    tax_identification_number = models.CharField(max_length=120)
    company_image = models.FileField(upload_to="companies/profile-images/", null=True, blank=True)
    company_location_state = models.CharField(max_length=500)
    preferred_deployment_states = models.CharField(max_length=500, blank=True, default="")
    company_location_city = models.CharField(max_length=120)
    company_address = models.CharField(max_length=255)
    head_office_address = models.CharField(max_length=255, blank=True, default="")
    company_website = models.URLField(max_length=255, blank=True, default="")
    company_sector = models.CharField(max_length=120)
    organization_type = models.CharField(max_length=120, blank=True, default="")
    staff_count_range = models.CharField(max_length=64, blank=True, default="")
    ppa_capacity = models.PositiveIntegerField(null=True, blank=True)
    office_location_count = models.PositiveIntegerField(null=True, blank=True)
    company_function = models.CharField(max_length=120, blank=True, default="")
    placement_type = models.CharField(max_length=255, blank=True, default="")
    monthly_allowance_offered = models.CharField(max_length=64, blank=True, default="")
    accommodation_provided = models.CharField(max_length=32, blank=True, default="")
    ppa_support = models.CharField(max_length=64, blank=True, default="")
    desired_corper_description = models.TextField()
    desired_qualification = models.TextField()
    desired_age_range = models.CharField(max_length=64)
    desired_field_of_study = models.TextField(default="")
    desired_university = models.TextField(blank=True, default="")
    desired_posting_states = models.CharField(max_length=500, blank=True, default="")
    desired_skills = models.TextField()
    desired_experience = models.TextField()
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(max_length=255, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True)
    directors_name = models.CharField(max_length=255, blank=True, default="")
    director_phone_number = models.CharField(max_length=20, blank=True, default="")
    terms_of_agreement_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_of_use_accepted_at = models.DateTimeField(null=True, blank=True)
    legal_acceptances = models.JSONField(default=dict, blank=True)
    directory_visibility_paused = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNSUBMITTED
    )
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.UNSUBMITTED
    )
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies_companyprofile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["company_location_state", "company_location_city"],
                name="company_profile_location_idx",
            ),
            models.Index(
                fields=["company_sector", "company_function"],
                name="company_profile_sector_fn_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company_registration_number"],
                condition=~Q(company_registration_number=""),
                name="companies_unique_reg_number",
            ),
            models.UniqueConstraint(
                fields=["tax_identification_number"],
                condition=~Q(tax_identification_number=""),
                name="companies_unique_tax_number",
            ),
        ]

    @classmethod
    def has_company_registration_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_company_registration_number(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(company_registration_number=normalized_value)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @classmethod
    def has_tax_identification_number(cls, value: str | None, *, exclude_pk=None) -> bool:
        normalized_value = normalize_tax_identification_number(value)
        if not normalized_value:
            return False
        queryset = cls.objects.filter(tax_identification_number=normalized_value)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    @property
    def profile_fields_complete(self) -> bool:
        required_values = (
            self.company_name,
            self.company_registration_number,
            self.tax_identification_number,
            self.company_image,
            self.company_location_state,
            self.preferred_deployment_states,
            self.company_location_city,
            self.company_address,
            self.company_sector,
            self.ppa_capacity,
            self.desired_corper_description,
            self.desired_qualification,
            self.desired_age_range,
            self.desired_field_of_study,
            self.desired_university,
            self.desired_posting_states,
            self.desired_skills,
            self.desired_experience,
            self.contact_name,
            self.contact_email,
            self.contact_phone,
        )
        return all(bool(value and str(value).strip()) for value in required_values)

    @property
    def verification_fields_complete(self) -> bool:
        required_values = (
            self.company_name,
            self.company_registration_number,
            self.tax_identification_number,
        )
        return all(bool(value and str(value).strip()) for value in required_values)

    @property
    def terms_accepted(self) -> bool:
        if self.legal_acceptances:
            return has_accepted_all_required_legal_documents(
                self.legal_acceptances, COMPANY_LEGAL_DOCUMENT_SLUGS
            )
        return bool(self.terms_of_agreement_accepted_at and self.terms_of_use_accepted_at)

    @property
    def is_complete(self) -> bool:
        return (
            self.profile_fields_complete
            and self.terms_accepted
            and self.verification_status == self.VerificationStatus.VERIFIED
        )

    def save(self, *args, **kwargs):
        self.company_name = str(self.company_name or "").strip()
        self.company_registration_number = normalize_company_registration_number(
            self.company_registration_number
        )
        self.tax_identification_number = normalize_tax_identification_number(
            self.tax_identification_number
        )
        super().save(*args, **kwargs)

    @property
    def next_profile_path(self) -> str:
        if (
            not self.verification_fields_complete
            or (
                self.terms_accepted
                and self.verification_status != self.VerificationStatus.VERIFIED
            )
        ):
            return "/company/verification"
        if not self.terms_accepted:
            return "/company/profile/terms"
        if self.is_complete:
            return "/company/corpers"
        return "/company/profile"

    @classmethod
    def directory_visibility_q(cls) -> Q:
        return Q(
            directory_visibility_paused=False,
            approval_status=cls.ApprovalStatus.APPROVED,
        )

    def __str__(self) -> str:
        return self.company_name
