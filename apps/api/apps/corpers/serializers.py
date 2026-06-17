from django.utils import timezone
from rest_framework import serializers

from apps.accounts.onboarding import (
    ensure_corper_can_be_approved,
    maybe_send_corper_approval_welcome_email,
)
from apps.accounts.models import User
from apps.common.legal import CORPER_LEGAL_DOCUMENT_SLUGS
from apps.accounts.presence import get_online_presence_cutoff
from apps.common.validators import validate_nigerian_mobile_number
from apps.search.services import viewer_can_see_corper_recommendations
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.services import corper_has_paid_access


def get_file_url(file_field) -> str | None:
    if not file_field:
        return None
    try:
        return file_field.url
    except (AttributeError, ValueError):
        return None


def resolve_corper_approval_status(profile: CorperProfile) -> str:
    if profile.approval_status != CorperProfile.ApprovalStatus.UNSUBMITTED:
        return profile.approval_status
    if profile.is_complete and profile.documents_verified:
        return CorperProfile.ApprovalStatus.APPROVED
    if profile.terms_accepted and (
        profile.verification_status
        in {
            CorperProfile.VerificationStatus.PENDING,
            CorperProfile.VerificationStatus.UNDER_REVIEW,
        }
    ):
        return CorperProfile.ApprovalStatus.PENDING
    if profile.verification_status == CorperProfile.VerificationStatus.REJECTED:
        return CorperProfile.ApprovalStatus.REJECTED
    return profile.approval_status


class CorperProfileValidationMixin:
    def validate_graduation_year(self, value):
        if value in (None, ""):
            return value

        current_year = timezone.now().year
        if value < 1973 or value > 2099:
            raise serializers.ValidationError("Select a graduation year between 1960 and 2099.")
        if value > current_year:
            raise serializers.ValidationError("Graduation year cannot be in the future.")
        return value

    def validate_mobile_number(self, value):
        normalized = validate_nigerian_mobile_number(value, require_international_format=True)
        instance = getattr(self, "instance", None)
        exclude_pk = None
        if isinstance(instance, CorperProfile):
            exclude_pk = instance.pk
        if CorperProfile.has_mobile_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("This mobile number is already in use.")
        return normalized

    def validate_university_matriculation_number(self, value):
        if not str(value or "").strip():
            return ""

        from apps.common.validators import validate_university_matriculation_number

        normalized = validate_university_matriculation_number(value)
        instance = getattr(self, "instance", None)
        exclude_pk = None
        if isinstance(instance, CorperProfile):
            exclude_pk = instance.pk
        if CorperProfile.has_university_matriculation_number(normalized, exclude_pk=exclude_pk):
            raise serializers.ValidationError("This university matriculation number has already been submitted.")
        return normalized


class CorperProfileSerializer(CorperProfileValidationMixin, serializers.ModelSerializer):
    REQUIRED_PROFILE_FIELDS = (
        "full_name",
        "date_of_birth",
        "posting_location_state",
        "batch",
        "stream",
        "field_of_study",
        "degree",
        "university",
        "graduation_year",
        "profile_photo",
        "mobile_number",
        "technical_skills",
        "soft_skills",
        "languages_spoken",
        "available_date",
        "bio",
    )
    email = serializers.EmailField(source="user.email", read_only=True)
    age = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    profile_fields_complete = serializers.BooleanField(read_only=True)
    terms_accepted = serializers.BooleanField(read_only=True)
    masked_nin_number = serializers.CharField(read_only=True)
    masked_callup_number = serializers.CharField(read_only=True)
    masked_state_code = serializers.CharField(read_only=True)
    nysc_callup_document = serializers.SerializerMethodField()
    nysc_state_code_document = serializers.SerializerMethodField()
    nin_number = serializers.SerializerMethodField()
    nysc_callup_number = serializers.SerializerMethodField()
    nysc_state_code = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()

    class Meta:
        model = CorperProfile
        fields = (
            "id",
            "email",
            "full_name",
            "first_name",
            "middle_name",
            "surname",
            "date_of_birth",
            "age",
            "gender",
            "state_of_origin",
            "country_of_birth",
            "posting_location_state",
            "batch",
            "stream",
            "university_matriculation_number",
            "field_of_study",
            "degree",
            "university",
            "graduation_year",
            "profile_photo",
            "nin_number",
            "masked_nin_number",
            "mobile_number",
            "nysc_callup_number",
            "masked_callup_number",
            "nysc_callup_document",
            "nysc_state_code",
            "masked_state_code",
            "nysc_state_code_document",
            "skill",
            "technical_skills",
            "soft_skills",
            "languages_spoken",
            "available_date",
            "bio",
            "preferred_sector",
            "preferred_organization_type",
            "preferred_placement_type",
            "preferred_monthly_allowance",
            "preferred_organization_experience",
            "legal_acceptances",
            "is_complete",
            "profile_fields_complete",
            "terms_accepted",
            "legal_acceptances",
            "approval_status",
            "verification_status",
            "biodata_verification_status",
            "nin_verification_status",
            "nysc_callup_verification_status",
            "nysc_state_code_verification_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "email",
            "is_complete",
            "profile_fields_complete",
            "terms_accepted",
            "legal_acceptances",
            "approval_status",
            "verification_status",
            "biodata_verification_status",
            "nin_verification_status",
            "nysc_callup_verification_status",
            "nysc_state_code_verification_status",
            "created_at",
            "updated_at",
        )

    def validate_profile_photo(self, value):
        if not value:
            return value
        max_size = 3 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Profile photo must be smaller than 3MB.")
        allowed_extensions = (".jpg", ".jpeg", ".png", ".webp")
        if not value.name.lower().endswith(allowed_extensions):
            raise serializers.ValidationError("Profile photo must be JPG, PNG, or WebP.")
        return value

    def validate_languages_spoken(self, value):
        return str(value or "").strip()

    def validate_technical_skills(self, value):
        return str(value or "").strip()

    def validate_soft_skills(self, value):
        return str(value or "").strip()

    def get_nin_number(self, obj):
        if obj.nin_verification_status != CorperProfile.SensitiveStatus.VERIFIED:
            return ""
        return obj.nin_number or ""

    def get_nysc_callup_number(self, obj):
        if obj.nysc_callup_verification_status != CorperProfile.SensitiveStatus.VERIFIED:
            return ""
        return obj.nysc_callup_number or ""

    def get_nysc_callup_document(self, obj):
        return get_file_url(obj.nysc_callup_document)

    def get_nysc_state_code(self, obj):
        if obj.nysc_state_code_verification_status != CorperProfile.SensitiveStatus.VERIFIED:
            return ""
        return obj.nysc_state_code or ""

    def get_nysc_state_code_document(self, obj):
        return get_file_url(obj.nysc_state_code_document)

    def get_approval_status(self, obj):
        return resolve_corper_approval_status(obj)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        technical_skills = str(attrs.get("technical_skills", getattr(self.instance, "technical_skills", ""))).strip()
        soft_skills = str(attrs.get("soft_skills", getattr(self.instance, "soft_skills", ""))).strip()
        skill_parts = [part for part in [technical_skills, soft_skills] if part]
        attrs["skill"] = " | ".join(skill_parts)

        if self.instance is None:
            return attrs

        missing_fields = {}
        for field_name in self.REQUIRED_PROFILE_FIELDS:
            value = attrs.get(field_name, getattr(self.instance, field_name, None))
            if field_name in {"graduation_year", "date_of_birth"}:
                is_missing = value in (None, "")
            elif field_name == "profile_photo":
                is_missing = not value
            else:
                is_missing = not value or not str(value).strip()

            if is_missing:
                missing_fields[field_name] = "Complete this field before saving your profile."

        if missing_fields:
            raise serializers.ValidationError(missing_fields)

        return attrs


class CorperDirectorySerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    is_online = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    match_reasons = serializers.SerializerMethodField()
    recommended = serializers.SerializerMethodField()

    class Meta:
        model = CorperProfile
        fields = (
            "id",
            "full_name",
            "age",
            "posting_location_state",
            "batch",
            "stream",
            "university_matriculation_number",
            "field_of_study",
            "degree",
            "university",
            "graduation_year",
            "profile_photo",
            "skill",
            "bio",
            "preferred_sector",
            "preferred_organization_type",
            "preferred_placement_type",
            "preferred_monthly_allowance",
            "preferred_organization_experience",
            "verification_status",
            "is_online",
            "match_score",
            "match_reasons",
            "recommended",
        )

    def get_is_online(self, obj):
        last_seen_at = getattr(obj.user, "last_seen_at", None)
        return bool(last_seen_at and last_seen_at >= get_online_presence_cutoff())

    def _viewer_can_see_recommendations(self) -> bool:
        request = self.context.get("request")
        return viewer_can_see_corper_recommendations(getattr(request, "user", None))

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


class CorperProfileSubmissionSerializer(serializers.Serializer):
    accepted_terms_of_agreement = serializers.BooleanField()
    accepted_terms_of_use = serializers.BooleanField()
    accepted_documents = serializers.ListField(
        child=serializers.ChoiceField(choices=CORPER_LEGAL_DOCUMENT_SLUGS),
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
            slug for slug in CORPER_LEGAL_DOCUMENT_SLUGS if slug not in set(attrs.get("accepted_documents", []))
        ]
        if missing_documents:
            raise serializers.ValidationError(
                {"accepted_documents": ["Accept every required legal document to continue."]}
            )
        return attrs

    def save(self, *, profile: CorperProfile):
        current_time = timezone.now()
        accepted_documents = set(self.validated_data["accepted_documents"])
        signer_name = profile.full_name or profile.user.email
        legal_acceptances = dict(profile.legal_acceptances or {})

        for slug in CORPER_LEGAL_DOCUMENT_SLUGS:
            if slug not in accepted_documents:
                continue
            legal_acceptances[slug] = {
                "accepted_at": current_time.isoformat(),
                "signer_name": signer_name,
                "signer_email": profile.user.email,
                "placeholders": {
                    "name": profile.full_name or signer_name,
                    "date": current_time.date().isoformat(),
                    "nysc_state_code": profile.nysc_state_code or "",
                    "nysc_callup_number": profile.nysc_callup_number or "",
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


class CorperDirectoryDetailSerializer(CorperDirectorySerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    gender = serializers.CharField(read_only=True)
    mobile_number = serializers.CharField(read_only=True)
    nysc_callup_number = serializers.CharField(read_only=True)
    nysc_service_year = serializers.SerializerMethodField()
    corper_has_expressed_interest = serializers.SerializerMethodField()
    company_interest_saved = serializers.SerializerMethodField()
    corper_has_paid_access = serializers.SerializerMethodField()

    class Meta(CorperDirectorySerializer.Meta):
        fields = CorperDirectorySerializer.Meta.fields + (
            "email",
            "gender",
            "mobile_number",
            "nysc_callup_number",
            "nysc_service_year",
            "corper_has_expressed_interest",
            "company_interest_saved",
            "corper_has_paid_access",
        )

    def get_nysc_service_year(self, obj):
        callup_number = (obj.nysc_callup_number or "").strip()
        parts = callup_number.split("/")
        if len(parts) < 3:
            return ""

        service_year = parts[2].strip()
        if len(service_year) != 4 or not service_year.isdigit():
            return ""

        return service_year

    def _get_interest(self, obj):
        request = self.context.get("request")
        if not request or request.user.role != User.Role.COMPANY:
            return None

        cache = getattr(self, "_company_interest_cache", None)
        if cache is None:
            cache = {}
            self._company_interest_cache = cache

        cache_key = str(obj.pk)
        if cache_key not in cache:
            from apps.interests.models import Interest

            cache[cache_key] = Interest.objects.filter(
                corper=obj,
                company__user=request.user,
            ).first()
        return cache[cache_key]

    def get_corper_has_expressed_interest(self, obj):
        interest = self._get_interest(obj)
        return bool(interest and interest.corper_expressed_at is not None)

    def get_company_interest_saved(self, obj):
        interest = self._get_interest(obj)
        return bool(interest and interest.company_expressed_at is not None)

    def get_corper_has_paid_access(self, obj):
        return corper_has_paid_access(user=obj.user)


class CorperAdminSerializer(CorperProfileValidationMixin, serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    email_verified = serializers.BooleanField(source="user.email_verified", read_only=True)
    masked_nin_number = serializers.CharField(read_only=True)
    masked_callup_number = serializers.CharField(read_only=True)
    masked_state_code = serializers.CharField(read_only=True)
    nysc_callup_document = serializers.SerializerMethodField()
    nysc_state_code_document = serializers.SerializerMethodField()
    is_complete = serializers.BooleanField(read_only=True)
    approval_status = serializers.ChoiceField(choices=CorperProfile.ApprovalStatus.choices, required=False)

    class Meta:
        model = CorperProfile
        fields = (
            "id",
            "email",
            "email_verified",
            "full_name",
            "first_name",
            "middle_name",
            "surname",
            "date_of_birth",
            "gender",
            "state_of_origin",
            "country_of_birth",
            "posting_location_state",
            "batch",
            "stream",
            "university_matriculation_number",
            "field_of_study",
            "degree",
            "university",
            "graduation_year",
            "profile_photo",
            "masked_nin_number",
            "mobile_number",
            "masked_callup_number",
            "nysc_callup_document",
            "masked_state_code",
            "nysc_state_code_document",
            "skill",
            "bio",
            "preferred_sector",
            "preferred_organization_type",
            "preferred_placement_type",
            "preferred_monthly_allowance",
            "preferred_organization_experience",
            "is_complete",
            "approval_status",
            "created_at",
            "updated_at",
        )

    def get_nysc_callup_document(self, obj):
        return get_file_url(obj.nysc_callup_document)

    def get_nysc_state_code_document(self, obj):
        return get_file_url(obj.nysc_state_code_document)

    def validate_approval_status(self, value):
        if value == CorperProfile.ApprovalStatus.APPROVED:
            ensure_corper_can_be_approved(self.instance)
        return value

    def update(self, instance, validated_data):
        previous_approval_status = instance.approval_status
        instance = super().update(instance, validated_data)
        maybe_send_corper_approval_welcome_email(
            instance,
            previous_status=previous_approval_status,
        )
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["approval_status"] = resolve_corper_approval_status(instance)
        return representation


class CorperAdminVerificationSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_created = serializers.SerializerMethodField()
    masked_nin_number = serializers.SerializerMethodField()
    masked_callup_number = serializers.SerializerMethodField()
    masked_state_code = serializers.SerializerMethodField()
    nysc_callup_document = serializers.SerializerMethodField()
    nysc_state_code_document = serializers.SerializerMethodField()
    biodata_verification_status = serializers.ChoiceField(choices=CorperProfile.SensitiveStatus.choices, read_only=True)
    verification_status = serializers.ChoiceField(choices=CorperProfile.VerificationStatus.choices, read_only=True)
    nin_verification_status = serializers.ChoiceField(choices=CorperProfile.SensitiveStatus.choices, required=False)
    nysc_callup_verification_status = serializers.ChoiceField(
        choices=CorperProfile.SensitiveStatus.choices, required=False
    )
    nysc_state_code_verification_status = serializers.ChoiceField(
        choices=CorperProfile.SensitiveStatus.choices, required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "profile_created",
            "biodata_verification_status",
            "masked_nin_number",
            "masked_callup_number",
            "nysc_callup_document",
            "masked_state_code",
            "nysc_state_code_document",
            "verification_status",
            "nin_verification_status",
            "nysc_callup_verification_status",
            "nysc_state_code_verification_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "full_name",
            "profile_created",
            "masked_nin_number",
            "masked_callup_number",
            "nysc_callup_document",
            "masked_state_code",
            "nysc_state_code_document",
            "created_at",
            "updated_at",
        )

    def _get_corper_profile(self, obj: User) -> CorperProfile | None:
        try:
            return obj.corper_profile
        except CorperProfile.DoesNotExist:
            return None

    def get_full_name(self, obj):
        profile = self._get_corper_profile(obj)
        return profile.full_name if profile else ""

    def get_profile_created(self, obj):
        return self._get_corper_profile(obj) is not None

    def get_masked_nin_number(self, obj):
        profile = self._get_corper_profile(obj)
        return profile.masked_nin_number if profile else ""

    def get_masked_callup_number(self, obj):
        profile = self._get_corper_profile(obj)
        return profile.masked_callup_number if profile else ""

    def get_nysc_callup_document(self, obj):
        profile = self._get_corper_profile(obj)
        return get_file_url(profile.nysc_callup_document) if profile else None

    def get_masked_state_code(self, obj):
        profile = self._get_corper_profile(obj)
        return profile.masked_state_code if profile else ""

    def get_nysc_state_code_document(self, obj):
        profile = self._get_corper_profile(obj)
        return get_file_url(profile.nysc_state_code_document) if profile else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        profile = self._get_corper_profile(instance)
        representation["verification_status"] = (
            profile.verification_status if profile else CorperProfile.VerificationStatus.PENDING
        )
        representation["biodata_verification_status"] = (
            profile.biodata_verification_status if profile else CorperProfile.SensitiveStatus.UNSUBMITTED
        )
        representation["nin_verification_status"] = (
            profile.nin_verification_status if profile else CorperProfile.SensitiveStatus.UNSUBMITTED
        )
        representation["nysc_callup_verification_status"] = (
            profile.nysc_callup_verification_status if profile else CorperProfile.SensitiveStatus.UNSUBMITTED
        )
        representation["nysc_state_code_verification_status"] = (
            profile.nysc_state_code_verification_status if profile else CorperProfile.SensitiveStatus.UNSUBMITTED
        )
        return representation

    def update(self, instance, validated_data):
        profile = ensure_corper_profile(instance)
        fields_to_update = ["updated_at"]
        for field_name in (
            "nin_verification_status",
            "nysc_callup_verification_status",
            "nysc_state_code_verification_status",
        ):
            if field_name in validated_data:
                setattr(profile, field_name, validated_data[field_name])
                fields_to_update.append(field_name)

        profile.save(update_fields=fields_to_update)
        instance.refresh_from_db()
        return instance
