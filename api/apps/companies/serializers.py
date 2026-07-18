from django.utils import timezone
from rest_framework import serializers
from PIL import UnidentifiedImageError

from apps.accounts.onboarding import (
    ensure_company_can_be_approved,
    maybe_send_company_approval_welcome_email,
)
from apps.accounts.models import User
from apps.common.legal import COMPANY_LEGAL_DOCUMENT_SLUGS
from apps.common.validators import validate_nigerian_mobile_number
from apps.companies.images import process_company_profile_image
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import (
    COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
    is_valid_company_registration_number,
    normalize_company_registration_number,
)
from apps.companies.validators import (
    TAX_IDENTIFICATION_NUMBER_VALIDATION_MESSAGE,
    is_valid_tax_identification_number,
    normalize_tax_identification_number,
)
from apps.search.services import viewer_can_see_company_recommendations


def resolve_company_approval_status(profile: CompanyProfile) -> str:
    if profile.approval_status != CompanyProfile.ApprovalStatus.UNSUBMITTED:
        return profile.approval_status
    if (
        profile.verification_status == CompanyProfile.VerificationStatus.VERIFIED
        and profile.profile_fields_complete
        and profile.terms_accepted
    ):
        return CompanyProfile.ApprovalStatus.APPROVED
    if profile.verification_status == CompanyProfile.VerificationStatus.REJECTED:
        return CompanyProfile.ApprovalStatus.REJECTED
    return profile.approval_status


class CompanyProfileSerializer(serializers.ModelSerializer):
    REQUIRED_PROFILE_FIELDS = (
        "company_name",
        "company_registration_number",
        "tax_identification_number",
        "company_image",
        "company_location_state",
        "preferred_deployment_states",
        "company_location_city",
        "company_address",
        "company_sector",
        "ppa_capacity",
        "desired_corper_description",
        "desired_qualification",
        "desired_age_range",
        "desired_field_of_study",
        "desired_university",
        "desired_posting_states",
        "desired_skills",
        "desired_experience",
        "contact_name",
        "contact_email",
        "contact_phone",
    )
    is_complete = serializers.BooleanField(read_only=True)
    profile_fields_complete = serializers.BooleanField(read_only=True)
    verification_fields_complete = serializers.BooleanField(read_only=True)
    terms_accepted = serializers.BooleanField(read_only=True)
    approval_status = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "company_name",
            "company_registration_number",
            "company_registration_date",
            "tax_identification_number",
            "company_image",
            "company_location_state",
            "preferred_deployment_states",
            "company_location_city",
            "company_address",
            "head_office_address",
            "company_website",
            "company_sector",
            "organization_type",
            "staff_count_range",
            "ppa_capacity",
            "office_location_count",
            "placement_type",
            "monthly_allowance_offered",
            "accommodation_provided",
            "ppa_support",
            "desired_corper_description",
            "desired_qualification",
            "desired_age_range",
            "desired_field_of_study",
            "desired_university",
            "desired_posting_states",
            "desired_skills",
            "desired_experience",
            "contact_name",
            "contact_email",
            "contact_phone",
            "directors_name",
            "director_phone_number",
            "legal_acceptances",
            "verification_status",
            "approval_status",
            "is_complete",
            "profile_fields_complete",
            "verification_fields_complete",
            "terms_accepted",
            "legal_acceptances",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "verification_status",
            "approval_status",
            "is_complete",
            "profile_fields_complete",
            "verification_fields_complete",
            "terms_accepted",
            "legal_acceptances",
            "created_at",
            "updated_at",
        )

    def validate_company_name(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Company name is required.")

        queryset = CompanyProfile.objects.filter(company_name__iexact=normalized)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A company with this name already exists.")
        return normalized

    def validate_company_image(self, value):
        if not value:
            return value
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Company image must be smaller than 10MB.")
        allowed_extensions = (".jpg", ".jpeg", ".png", ".webp")
        if not value.name.lower().endswith(allowed_extensions):
            raise serializers.ValidationError("Company image must be JPG, PNG, or WebP.")
        try:
            return process_company_profile_image(value)
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError("Upload a valid JPG, PNG, or WebP company image.")

    def validate_contact_phone(self, value):
        return validate_nigerian_mobile_number(
            value,
            required=True,
            field_label="Contact number",
            require_international_format=True,
        )

    def validate_contact_name(self, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise serializers.ValidationError("Contact name is required.")
        return normalized

    def validate_ppa_capacity(self, value):
        if value is None:
            raise serializers.ValidationError("PPA capacity is required.")
        if value < 1:
            raise serializers.ValidationError("PPA capacity must be at least 1.")
        return value

    def validate_office_location_count(self, value):
        if value is None:
            return value
        if value < 1:
            raise serializers.ValidationError("Number of office locations must be at least 1.")
        return value

    def validate_director_phone_number(self, value):
        return validate_nigerian_mobile_number(
            value,
            required=False,
            field_label="Director phone number",
            require_international_format=True,
        )

    def validate_company_registration_number(self, value):
        normalized = normalize_company_registration_number(value)
        if not normalized:
            raise serializers.ValidationError("Company registration number is required.")
        if not is_valid_company_registration_number(normalized):
            raise serializers.ValidationError(COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE)
        exclude_pk = self.instance.pk if self.instance is not None else None
        if CompanyProfile.has_company_registration_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("A company with this registration number already exists.")
        return normalized

    def validate_tax_identification_number(self, value):
        normalized = normalize_tax_identification_number(value)
        if not normalized:
            raise serializers.ValidationError("Tax identification number is required.")
        if not is_valid_tax_identification_number(normalized):
            raise serializers.ValidationError(TAX_IDENTIFICATION_NUMBER_VALIDATION_MESSAGE)
        exclude_pk = self.instance.pk if self.instance is not None else None
        if CompanyProfile.has_tax_identification_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("A company with this tax identification number already exists.")
        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance is None:
            return attrs

        missing_fields = {}
        for field_name in self.REQUIRED_PROFILE_FIELDS:
            value = attrs.get(field_name, getattr(self.instance, field_name, None))
            if field_name in {"company_image"}:
                is_missing = not value
            else:
                is_missing = not value or not str(value).strip()

            if is_missing:
                missing_fields[field_name] = "Complete this field before saving your profile."

        if missing_fields:
            raise serializers.ValidationError(missing_fields)

        return attrs

    def get_approval_status(self, obj):
        return resolve_company_approval_status(obj)


class CompanyVerificationSerializer(serializers.ModelSerializer):
    verification_fields_complete = serializers.BooleanField(read_only=True)
    company_location_state = serializers.CharField(required=False, allow_blank=True)
    approval_status = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "company_name",
            "company_registration_number",
            "company_registration_date",
            "company_location_state",
            "tax_identification_number",
            "verification_status",
            "approval_status",
            "verification_fields_complete",
            "terms_accepted",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "verification_status",
            "approval_status",
            "verification_fields_complete",
            "terms_accepted",
            "created_at",
            "updated_at",
        )

    def validate_company_name(self, value):
        return CompanyProfileSerializer.validate_company_name(self, value)

    def validate_company_registration_number(self, value):
        return CompanyProfileSerializer.validate_company_registration_number(self, value)

    def validate_tax_identification_number(self, value):
        return CompanyProfileSerializer.validate_tax_identification_number(self, value)

    def validate_company_location_state(self, value):
        return str(value or "").strip()

    def get_approval_status(self, obj):
        return resolve_company_approval_status(obj)


class CompanyDiscoverySerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    summary_description = serializers.CharField(source="desired_corper_description")
    match_score = serializers.SerializerMethodField()
    match_reasons = serializers.SerializerMethodField()
    recommended = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "company_name",
            "company_image",
            "location",
            "company_sector",
            "summary_description",
            "match_score",
            "match_reasons",
            "recommended",
        )

    def _viewer_can_see_recommendations(self) -> bool:
        request = self.context.get("request")
        return viewer_can_see_company_recommendations(getattr(request, "user", None))

    def get_location(self, obj):
        return f"{obj.company_location_city}, {obj.company_location_state}".strip(", ")

    def get_match_score(self, obj):
        if not self._viewer_can_see_recommendations():
            return None
        return int(getattr(obj, "match_score", 0))

    def get_match_reasons(self, obj):
        if not self._viewer_can_see_recommendations():
            return []
        return list(getattr(obj, "match_reasons", []))

    def get_recommended(self, obj):
        if not self._viewer_can_see_recommendations():
            return False
        return bool(getattr(obj, "recommended", False))


class CompanyDirectoryDetailSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    summary_description = serializers.CharField(source="desired_corper_description")
    match_score = serializers.SerializerMethodField()
    match_reasons = serializers.SerializerMethodField()
    recommended = serializers.SerializerMethodField()
    corper_has_expressed_interest = serializers.SerializerMethodField()
    company_has_expressed_interest = serializers.SerializerMethodField()

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "company_name",
            "company_image",
            "location",
            "company_location_state",
            "company_location_city",
            "company_sector",
            "summary_description",
            "desired_qualification",
            "desired_age_range",
            "desired_field_of_study",
            "desired_university",
            "desired_posting_states",
            "desired_skills",
            "desired_experience",
            "match_score",
            "match_reasons",
            "recommended",
            "corper_has_expressed_interest",
            "company_has_expressed_interest",
        )

    def _viewer_can_see_recommendations(self) -> bool:
        request = self.context.get("request")
        return viewer_can_see_company_recommendations(getattr(request, "user", None))

    def get_location(self, obj):
        return f"{obj.company_location_city}, {obj.company_location_state}".strip(", ")

    def get_match_score(self, obj):
        if not self._viewer_can_see_recommendations():
            return None
        return int(getattr(obj, "match_score", 0))

    def get_match_reasons(self, obj):
        if not self._viewer_can_see_recommendations():
            return []
        return list(getattr(obj, "match_reasons", []))

    def get_recommended(self, obj):
        if not self._viewer_can_see_recommendations():
            return False
        return bool(getattr(obj, "recommended", False))

    def _get_interest(self, obj):
        request = self.context.get("request")
        if not request or request.user.role != User.Role.CORPER:
            return None

        cache = getattr(self, "_corper_interest_cache", None)
        if cache is None:
            cache = {}
            self._corper_interest_cache = cache

        cache_key = str(obj.pk)
        if cache_key not in cache:
            from apps.interests.models import Interest

            cache[cache_key] = Interest.objects.filter(
                company=obj,
                corper__user=request.user,
            ).first()
        return cache[cache_key]

    def get_corper_has_expressed_interest(self, obj):
        interest = self._get_interest(obj)
        return bool(interest and interest.corper_expressed_at is not None)

    def get_company_has_expressed_interest(self, obj):
        interest = self._get_interest(obj)
        return bool(interest and interest.company_expressed_at is not None)


class CompanyAdminSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    email_verified = serializers.BooleanField(source="user.email_verified", read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    verification_fields_complete = serializers.BooleanField(read_only=True)
    profile_fields_complete = serializers.BooleanField(read_only=True)
    verification_status = serializers.ChoiceField(choices=CompanyProfile.VerificationStatus.choices, read_only=True)
    approval_status = serializers.ChoiceField(choices=CompanyProfile.ApprovalStatus.choices, required=False)

    class Meta:
        model = CompanyProfile
        fields = (
            "id",
            "email",
            "email_verified",
            "company_name",
            "company_registration_number",
            "company_registration_date",
            "tax_identification_number",
            "company_image",
            "company_location_state",
            "preferred_deployment_states",
            "company_location_city",
            "company_address",
            "head_office_address",
            "company_website",
            "company_sector",
            "organization_type",
            "staff_count_range",
            "placement_type",
            "monthly_allowance_offered",
            "accommodation_provided",
            "ppa_support",
            "desired_corper_description",
            "desired_qualification",
            "desired_age_range",
            "desired_field_of_study",
            "desired_university",
            "desired_posting_states",
            "desired_skills",
            "desired_experience",
            "contact_name",
            "contact_email",
            "contact_phone",
            "directors_name",
            "director_phone_number",
            "verification_status",
            "approval_status",
            "is_complete",
            "profile_fields_complete",
            "verification_fields_complete",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "email",
            "email_verified",
            "verification_status",
            "is_complete",
            "profile_fields_complete",
            "verification_fields_complete",
            "created_at",
            "updated_at",
        )

    def validate_tax_identification_number(self, value):
        normalized = normalize_tax_identification_number(value)
        if not normalized:
            raise serializers.ValidationError("Tax identification number is required.")
        if not is_valid_tax_identification_number(normalized):
            raise serializers.ValidationError(TAX_IDENTIFICATION_NUMBER_VALIDATION_MESSAGE)
        exclude_pk = self.instance.pk if self.instance is not None else None
        if CompanyProfile.has_tax_identification_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("A company with this tax identification number already exists.")
        return normalized

    def validate_company_registration_number(self, value):
        normalized = normalize_company_registration_number(value)
        if not normalized:
            raise serializers.ValidationError("Company registration number is required.")
        if not is_valid_company_registration_number(normalized):
            raise serializers.ValidationError(COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE)
        exclude_pk = self.instance.pk if self.instance is not None else None
        if CompanyProfile.has_company_registration_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("A company with this registration number already exists.")
        return normalized

    def validate_director_phone_number(self, value):
        return validate_nigerian_mobile_number(
            value,
            required=False,
            field_label="Director phone number",
            require_international_format=True,
        )

    def validate_approval_status(self, value):
        if value == CompanyProfile.ApprovalStatus.APPROVED:
            ensure_company_can_be_approved(self.instance)
        return value

    def update(self, instance, validated_data):
        previous_approval_status = instance.approval_status
        instance = super().update(instance, validated_data)
        maybe_send_company_approval_welcome_email(
            instance,
            previous_status=previous_approval_status,
        )
        return instance


class CompanyProfileSubmissionSerializer(serializers.Serializer):
    accepted_terms_of_agreement = serializers.BooleanField()
    accepted_terms_of_use = serializers.BooleanField()
    accepted_documents = serializers.ListField(
        child=serializers.ChoiceField(choices=COMPANY_LEGAL_DOCUMENT_SLUGS),
        allow_empty=False,
        write_only=True,
    )

    def validate(self, attrs):
        if not attrs["accepted_terms_of_agreement"]:
            raise serializers.ValidationError(
                {"accepted_terms_of_agreement": ["Accept the Terms of Agreement to continue."]}
            )
        if not attrs["accepted_terms_of_use"]:
            raise serializers.ValidationError({"accepted_terms_of_use": ["Accept the Terms of Use to continue."]})
        missing_documents = [
            slug for slug in COMPANY_LEGAL_DOCUMENT_SLUGS if slug not in set(attrs.get("accepted_documents", []))
        ]
        if missing_documents:
            raise serializers.ValidationError(
                {"accepted_documents": ["Accept every required legal document to continue."]}
            )
        return attrs

    def save(self, *, profile: CompanyProfile):
        current_time = timezone.now()
        accepted_documents = set(self.validated_data["accepted_documents"])
        signer_name = profile.contact_name or profile.company_name or profile.user.email
        legal_acceptances = dict(profile.legal_acceptances or {})

        for slug in COMPANY_LEGAL_DOCUMENT_SLUGS:
            if slug not in accepted_documents:
                continue
            legal_acceptances[slug] = {
                "accepted_at": current_time.isoformat(),
                "signer_name": signer_name,
                "signer_email": profile.user.email,
                "placeholders": {
                    "name": signer_name,
                    "date": current_time.date().isoformat(),
                    "company_name": profile.company_name or "",
                },
            }

        profile.terms_of_agreement_accepted_at = current_time
        profile.terms_of_use_accepted_at = current_time
        profile.legal_acceptances = legal_acceptances
        profile.save(
            update_fields=[
                "terms_of_agreement_accepted_at",
                "terms_of_use_accepted_at",
                "legal_acceptances",
                "updated_at",
            ]
        )
        return profile
