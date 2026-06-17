from rest_framework import serializers

from apps.common.utils import mask_identifier
from apps.common.validators import (
    validate_nigerian_mobile_number,
    validate_nin_number,
    validate_nysc_callup_number,
    validate_nysc_state_code,
    validate_university_matriculation_number,
)
from apps.corpers.models import CorperProfile
from apps.verification.models import VerificationAttempt


def get_file_url(file_field) -> str | None:
    if not file_field:
        return None
    try:
        return file_field.url
    except (AttributeError, ValueError):
        return None


class VerificationSubmissionSerializer(serializers.Serializer):
    ALLOWED_DOCUMENT_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".webp")
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024

    verification_type = serializers.ChoiceField(choices=VerificationAttempt.VerificationType.choices)
    submitted_value = serializers.CharField(max_length=255, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    surname = serializers.CharField(max_length=120, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=CorperProfile.Gender.choices, required=False)
    mobile_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    state_of_origin = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country_of_birth = serializers.CharField(max_length=120, required=False, allow_blank=True)
    university_matriculation_number = serializers.CharField(max_length=120, required=False, allow_blank=True)
    document = serializers.FileField(required=False, allow_empty_file=False)

    def validate_document(self, value):
        if not value:
            return value
        if value.size > self.MAX_DOCUMENT_SIZE:
            raise serializers.ValidationError("Document must be smaller than 5MB.")
        if not value.name.lower().endswith(self.ALLOWED_DOCUMENT_EXTENSIONS):
            raise serializers.ValidationError("Document must be PDF, JPG, PNG, or WebP.")
        return value

    def validate(self, attrs):
        verification_type = attrs["verification_type"]
        submitted_value = attrs.get("submitted_value", "").strip()
        full_name = " ".join(str(attrs.get("full_name", "")).split())
        first_name = " ".join(str(attrs.get("first_name", "")).split())
        middle_name = " ".join(str(attrs.get("middle_name", "")).split())
        surname = " ".join(str(attrs.get("surname", "")).split())
        university_matriculation_number = str(
            attrs.get("university_matriculation_number", "")
        ).strip()
        state_of_origin = " ".join(str(attrs.get("state_of_origin", "")).split())
        country_of_birth = " ".join(str(attrs.get("country_of_birth", "")).split())
        document = attrs.get("document")

        if full_name and not first_name and not surname:
            name_parts = full_name.split()
            if name_parts:
                first_name = name_parts[0]
                surname = name_parts[-1] if len(name_parts) > 1 else ""
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
        full_name = " ".join(part for part in (first_name, middle_name, surname) if part)

        if verification_type in {
            VerificationAttempt.VerificationType.NIN,
            VerificationAttempt.VerificationType.CALLUP,
            VerificationAttempt.VerificationType.STATE_CODE,
        } and not submitted_value:
            raise serializers.ValidationError({"submitted_value": "This value is required."})
        if verification_type == VerificationAttempt.VerificationType.BIODATA:
            errors = {}
            if not first_name:
                errors["first_name"] = "This value is required."
            if not surname:
                errors["surname"] = "This value is required."
            if not attrs.get("date_of_birth"):
                errors["date_of_birth"] = "This value is required."
            if not attrs.get("gender"):
                errors["gender"] = "This value is required."
            if not str(attrs.get("mobile_number", "")).strip():
                errors["mobile_number"] = "This value is required."
            if errors:
                raise serializers.ValidationError(errors)
        if verification_type in {
            VerificationAttempt.VerificationType.CALLUP,
            VerificationAttempt.VerificationType.STATE_CODE,
        } and not document:
            raise serializers.ValidationError({"document": "Upload the NYSC document."})

        if verification_type == VerificationAttempt.VerificationType.BIODATA:
            try:
                attrs["mobile_number"] = validate_nigerian_mobile_number(
                    attrs.get("mobile_number"),
                    required=True,
                    field_label="Mobile number",
                    require_international_format=False,
                )
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"mobile_number": exc.detail}) from exc

        try:
            if verification_type == VerificationAttempt.VerificationType.NIN:
                submitted_value = validate_nin_number(submitted_value)
            elif verification_type == VerificationAttempt.VerificationType.CALLUP:
                submitted_value = validate_nysc_callup_number(submitted_value)
            elif verification_type == VerificationAttempt.VerificationType.STATE_CODE:
                submitted_value = validate_nysc_state_code(submitted_value)
            elif verification_type == VerificationAttempt.VerificationType.BIODATA:
                if university_matriculation_number:
                    university_matriculation_number = validate_university_matriculation_number(
                        university_matriculation_number
                    )
        except serializers.ValidationError as exc:
            if verification_type == VerificationAttempt.VerificationType.BIODATA:
                if university_matriculation_number:
                    raise serializers.ValidationError(
                        {"university_matriculation_number": exc.detail}
                    ) from exc
                raise serializers.ValidationError({"detail": exc.detail}) from exc
            raise serializers.ValidationError({"submitted_value": exc.detail}) from exc

        attrs["submitted_value"] = submitted_value
        attrs["full_name"] = full_name
        attrs["first_name"] = first_name
        attrs["middle_name"] = middle_name
        attrs["surname"] = surname
        attrs["state_of_origin"] = state_of_origin
        attrs["country_of_birth"] = country_of_birth
        attrs["university_matriculation_number"] = university_matriculation_number
        return attrs


class VerificationAttemptSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="corper.user.email", read_only=True)
    corper_name = serializers.CharField(source="corper.full_name", read_only=True)
    reviewer_email = serializers.EmailField(
        source="reviewed_by.email",
        read_only=True,
        allow_null=True,
        default=None,
    )
    document_name = serializers.SerializerMethodField()
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = VerificationAttempt
        fields = (
            "id",
            "corper",
            "user_email",
            "corper_name",
            "verification_type",
            "status",
            "submitted_value_masked",
            "metadata",
            "reviewed_by",
            "reviewer_email",
            "review_note",
            "document_name",
            "document_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def _document_field(self, obj):
        if obj.verification_type == VerificationAttempt.VerificationType.CALLUP:
            return obj.corper.nysc_callup_document
        if obj.verification_type == VerificationAttempt.VerificationType.STATE_CODE:
            return obj.corper.nysc_state_code_document
        return None

    def get_document_name(self, obj):
        metadata = obj.metadata or {}
        if metadata.get("document_name"):
            return str(metadata["document_name"])
        file_field = self._document_field(obj)
        if not file_field:
            return None
        return str(file_field.name).rsplit("/", 1)[-1] or None

    def get_document_url(self, obj):
        metadata = obj.metadata or {}
        if metadata.get("document_path"):
            return str(metadata["document_path"])
        return get_file_url(self._document_field(obj))


class VerificationReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            VerificationAttempt.Status.APPROVED,
            VerificationAttempt.Status.REJECTED,
        ]
    )
    review_note = serializers.CharField(required=False, allow_blank=True)


def masked_value(value: str) -> str:
    return mask_identifier(value, prefix=2, suffix=2)
