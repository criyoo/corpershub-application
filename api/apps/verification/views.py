import logging
import re

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import deleted_account_biodata_exists, deleted_account_nin_exists
from apps.audit.services import log_audit_event
from apps.common.permissions import IsAdminUserRole, IsCorperUser
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.corpers.models import CorperProfile, hash_sensitive_identifier
from apps.corpers.services import ensure_corper_profile
from apps.verification.verification_service import (
    extract_verification_message as extract_dikript_message,
    verification_lookup as dikript_lookup,
)
from apps.verification.models import DikriptVerificationCache, VerificationAttempt
from apps.verification.serializers import (
    VerificationAttemptSerializer,
    VerificationReviewSerializer,
    VerificationSubmissionSerializer,
    masked_value,
)

logger = logging.getLogger(__name__)

_DUPLICATE_FIELD_ERROR_MESSAGES = {
    "mobile_number": "This mobile number has already been submitted.",
    "university_matriculation_number": "This university matriculation number has already been submitted.",
    "nin_lookup_hash": "This NIN number has already been submitted.",
    "nysc_callup_lookup_hash": "This NYSC call-up number has already been submitted.",
    "nysc_state_code_lookup_hash": "This NYSC state code has already been submitted.",
}

_DUPLICATE_CONSTRAINT_ERROR_MESSAGES = {
    "corpers_unique_mobile_number": _DUPLICATE_FIELD_ERROR_MESSAGES["mobile_number"],
    "corpers_unique_matric_number": _DUPLICATE_FIELD_ERROR_MESSAGES["university_matriculation_number"],
    "corpers_unique_nin_hash": _DUPLICATE_FIELD_ERROR_MESSAGES["nin_lookup_hash"],
    "corpers_unique_callup_hash": _DUPLICATE_FIELD_ERROR_MESSAGES["nysc_callup_lookup_hash"],
    "corpers_unique_state_code_hash": _DUPLICATE_FIELD_ERROR_MESSAGES["nysc_state_code_lookup_hash"],
}

_KNOWN_HUMANIZED_ERROR_MESSAGES = tuple(
    dict.fromkeys(
        [
            *_DUPLICATE_FIELD_ERROR_MESSAGES.values(),
            "Your NIN has already been verified.",
            "Your NYSC call-up number has already been verified.",
            "Your NYSC state code has already been verified.",
            "These biodata details are linked to a previously deleted account. Contact support for assistance.",
            "This NIN number is linked to a previously deleted account. Contact support.",
        ]
    )
)


def _extract_error_message(detail) -> str:
    if isinstance(detail, dict):
        for value in detail.values():
            message = _extract_error_message(value)
            if message:
                return message
        return ""
    if isinstance(detail, (list, tuple)):
        for item in detail:
            message = _extract_error_message(item)
            if message:
                return message
        return ""
    return str(detail).strip()


def _record_failed_attempt(*, corper, verification_type: str, submitted_value: str, error_message: str):
    if verification_type not in dict(VerificationAttempt.VerificationType.choices):
        return None

    return VerificationAttempt.objects.create(
        corper=corper,
        verification_type=verification_type,
        status=VerificationAttempt.Status.FAILED,
        submitted_value_masked=masked_value(submitted_value) if submitted_value else "",
        metadata={"submitted": False, "error": error_message},
        review_note=error_message,
    )


def _humanize_integrity_error(error: IntegrityError) -> str:
    cause = getattr(error, "__cause__", None) or getattr(error, "__context__", None)
    constraint_name = str(getattr(getattr(cause, "diag", None), "constraint_name", "") or "").strip()
    if constraint_name in _DUPLICATE_CONSTRAINT_ERROR_MESSAGES:
        return _DUPLICATE_CONSTRAINT_ERROR_MESSAGES[constraint_name]

    detail = str(getattr(getattr(cause, "diag", None), "message_detail", "") or "").strip()
    message = detail or " ".join(str(part).strip() for part in error.args if str(part).strip()) or str(error)
    return _humanize_duplicate_error_message(message)


def _humanize_duplicate_error_message(message: str) -> str:
    normalized_message = str(message or "").strip()
    if not normalized_message:
        return ""

    lower_message = normalized_message.lower()
    for constraint_name, humanized_message in _DUPLICATE_CONSTRAINT_ERROR_MESSAGES.items():
        if constraint_name.lower() in lower_message:
            return humanized_message

    match = re.search(r"Key \((?P<field>[^)]+)\)=\((?P<value>[^)]*)\) already exists", message, re.IGNORECASE)
    if match:
        field_name = str(match.group("field") or "").strip()
        if field_name in _DUPLICATE_FIELD_ERROR_MESSAGES:
            return _DUPLICATE_FIELD_ERROR_MESSAGES[field_name]
        return f"{field_name.replace('_', ' ').capitalize()} already exists."

    if "duplicate key value violates unique constraint" in lower_message:
        return "This record already exists."

    return ""


def _resolve_persistence_error_message(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return _extract_error_message(error.detail)

    if isinstance(error, IntegrityError):
        integrity_message = _humanize_integrity_error(error)
        if integrity_message:
            return integrity_message

    cause = getattr(error, "__cause__", None) or getattr(error, "__context__", None)
    detail = str(getattr(getattr(cause, "diag", None), "message_detail", "") or "").strip()
    combined_message = " ".join(
        part
        for part in [
            detail,
            " ".join(str(part).strip() for part in getattr(error, "args", ()) if str(part).strip()),
            str(cause).strip() if cause else "",
            str(error).strip(),
        ]
        if part
    ).strip()

    duplicate_message = _humanize_duplicate_error_message(combined_message)
    if duplicate_message:
        return duplicate_message

    lower_combined_message = combined_message.lower()
    for humanized_message in _KNOWN_HUMANIZED_ERROR_MESSAGES:
        if humanized_message.lower() in lower_combined_message:
            return humanized_message

    return ""


def _mask_biodata_submission(full_name: str, date_of_birth, university_matriculation_number: str) -> str:
    parts = [
        full_name.strip(),
        str(date_of_birth).strip() if date_of_birth else "",
        masked_value(university_matriculation_number) if university_matriculation_number else "",
    ]
    return " | ".join(part for part in parts if part)


def _build_biodata_metadata(serializer) -> dict:
    return {
        "submitted": True,
        "full_name": serializer.validated_data.get("full_name", ""),
        "first_name": serializer.validated_data.get("first_name", ""),
        "middle_name": serializer.validated_data.get("middle_name", ""),
        "surname": serializer.validated_data.get("surname", ""),
        "date_of_birth": str(serializer.validated_data.get("date_of_birth") or ""),
        "gender": serializer.validated_data.get("gender", ""),
        "mobile_number": serializer.validated_data.get("mobile_number", ""),
        "state_of_origin": serializer.validated_data.get("state_of_origin", ""),
        "country_of_birth": serializer.validated_data.get("country_of_birth", ""),
        "university_matriculation_number": serializer.validated_data.get("university_matriculation_number", ""),
    }


def _persist_biodata_snapshot(*, corper: CorperProfile, metadata: dict):
    corper.full_name = str(metadata.get("full_name", "")).strip()
    corper.first_name = str(metadata.get("first_name", "")).strip()
    corper.middle_name = str(metadata.get("middle_name", "")).strip()
    corper.surname = str(metadata.get("surname", "")).strip()
    corper.date_of_birth = metadata.get("date_of_birth") or None
    corper.gender = str(metadata.get("gender", "")).strip().lower()
    corper.mobile_number = str(metadata.get("mobile_number", "")).strip()
    corper.state_of_origin = str(metadata.get("state_of_origin", "")).strip()
    corper.country_of_birth = str(metadata.get("country_of_birth", "")).strip()
    corper.university_matriculation_number = str(metadata.get("university_matriculation_number", "")).strip()
    corper.biodata_verification_status = CorperProfile.SensitiveStatus.PENDING
    corper.save(
        update_fields=[
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
            "biodata_verification_status",
            "updated_at",
        ]
    )
def _normalize_nin_value(value) -> str:
    digits = re.sub(r"\D", "", str(value or "").strip())
    return digits


class VerificationAttemptListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VerificationAttemptSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsCorperUser()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        if request.user.role not in {"corper", "admin"}:
            return Response({"detail": "You do not have permission to view verification attempts."}, status=403)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = VerificationAttempt.objects.select_related("corper", "reviewed_by").all()
        if self.request.user.role == "admin":
            return queryset
        return queryset.filter(corper__user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = VerificationSubmissionSerializer(data=request.data)
        corper = ensure_corper_profile(request.user)
        if not serializer.is_valid():
            _record_failed_attempt(
                corper=corper,
                verification_type=str(request.data.get("verification_type", "")).strip().lower(),
                submitted_value=str(request.data.get("submitted_value", "")).strip(),
                error_message=_extract_error_message(serializer.errors),
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        verification_type = serializer.validated_data["verification_type"]
        submitted_value = serializer.validated_data.get("submitted_value", "")
        full_name = serializer.validated_data.get("full_name", "")
        date_of_birth = serializer.validated_data.get("date_of_birth")
        mobile_number = serializer.validated_data.get("mobile_number", "")
        university_matriculation_number = serializer.validated_data.get("university_matriculation_number", "")
        document = serializer.validated_data.get("document")

        if (
            verification_type == VerificationAttempt.VerificationType.BIODATA
            and corper.biodata_verification_status == CorperProfile.SensitiveStatus.VERIFIED
        ):
            latest_attempt = (
                corper.verification_attempts.filter(
                    verification_type=VerificationAttempt.VerificationType.BIODATA
                )
                .exclude(status=VerificationAttempt.Status.FAILED)
                .order_by("-created_at")
                .first()
            )
            if latest_attempt:
                return Response(VerificationAttemptSerializer(latest_attempt).data, status=status.HTTP_200_OK)
            return Response({"detail": "Biodata verification is complete."}, status=status.HTTP_200_OK)

        if verification_type == VerificationAttempt.VerificationType.BIODATA and deleted_account_biodata_exists(
            full_name=full_name,
            date_of_birth=date_of_birth,
        ):
            error_message = (
                "These biodata details are linked to a previously deleted account. Contact support for assistance."
            )
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=university_matriculation_number,
                error_message=error_message,
            )
            return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        if (
            verification_type == VerificationAttempt.VerificationType.BIODATA
            and CorperProfile.has_university_matriculation_number(
                university_matriculation_number,
                exclude_pk=corper.pk,
            )
        ):
            error_message = "This university matriculation number has already been submitted."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=university_matriculation_number,
                error_message=error_message,
            )
            return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        if verification_type == VerificationAttempt.VerificationType.BIODATA and CorperProfile.has_mobile_number(
            mobile_number,
            exclude_pk=corper.pk,
        ):
            error_message = "This mobile number has already been submitted."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=mobile_number,
                error_message=error_message,
            )
            return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)

        if (
            verification_type == VerificationAttempt.VerificationType.NIN
            and corper.nin_verification_status == CorperProfile.SensitiveStatus.VERIFIED
        ):
            error_message = "Your NIN has already been verified."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=submitted_value,
                error_message=error_message,
            )
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            verification_type == VerificationAttempt.VerificationType.CALLUP
            and corper.nysc_callup_verification_status == CorperProfile.SensitiveStatus.VERIFIED
        ):
            error_message = "Your NYSC call-up number has already been verified."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=submitted_value,
                error_message=error_message,
            )
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            verification_type == VerificationAttempt.VerificationType.STATE_CODE
            and corper.nysc_state_code_verification_status == CorperProfile.SensitiveStatus.VERIFIED
        ):
            error_message = "Your NYSC state code has already been verified."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=submitted_value,
                error_message=error_message,
            )
            return Response(
                {"detail": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification_type == VerificationAttempt.VerificationType.NIN:
            if deleted_account_nin_exists(submitted_value):
                error_message = "This NIN number is linked to a previously deleted account. Contact support."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
            submitted_hash = hash_sensitive_identifier(submitted_value)
            if (
                corper.nin_lookup_hash == submitted_hash
                and corper.nin_verification_status == CorperProfile.SensitiveStatus.VERIFIED
            ):
                error_message = "This NIN number has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if CorperProfile.has_nin_number(submitted_value, exclude_pk=corper.pk):
                error_message = "This NIN number has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if verification_type == VerificationAttempt.VerificationType.CALLUP:
            submitted_hash = hash_sensitive_identifier(submitted_value)
            if (
                corper.nysc_callup_lookup_hash == submitted_hash
                and corper.nysc_callup_verification_status == CorperProfile.SensitiveStatus.VERIFIED
            ):
                error_message = "This NYSC call-up number has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if CorperProfile.has_nysc_callup_number(submitted_value, exclude_pk=corper.pk):
                error_message = "This NYSC call-up number has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if verification_type == VerificationAttempt.VerificationType.STATE_CODE:
            submitted_hash = hash_sensitive_identifier(submitted_value)
            if (
                corper.nysc_state_code_lookup_hash == submitted_hash
                and corper.nysc_state_code_verification_status == CorperProfile.SensitiveStatus.VERIFIED
            ):
                error_message = "This NYSC state code has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if CorperProfile.has_nysc_state_code(submitted_value, exclude_pk=corper.pk):
                error_message = "This NYSC state code has already been submitted."
                _record_failed_attempt(
                    corper=corper,
                    verification_type=verification_type,
                    submitted_value=submitted_value,
                    error_message=error_message,
                )
                return Response(
                    {"detail": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                if verification_type == VerificationAttempt.VerificationType.BIODATA:
                    attempt = VerificationAttempt.objects.create(
                        corper=corper,
                        verification_type=verification_type,
                        submitted_value_masked=_mask_biodata_submission(
                            full_name,
                            date_of_birth,
                            university_matriculation_number,
                        ),
                        metadata=_build_biodata_metadata(serializer),
                    )
                    _persist_biodata_snapshot(corper=corper, metadata=attempt.metadata or {})
                elif verification_type == VerificationAttempt.VerificationType.NIN:
                    payload = dikript_lookup(
                        verification_type=DikriptVerificationCache.VerificationType.NIN,
                        path=settings.DIKRIPT_NIN_API_URL,
                        lookup_value=submitted_value,
                        query={"nin": submitted_value},
                    )
                    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
                    if not payload.get("status") or not data:
                        message = extract_dikript_message(payload) or "No NIN record was found for this number."
                        attempt = VerificationAttempt.objects.create(
                            corper=corper,
                            verification_type=verification_type,
                            status=VerificationAttempt.Status.REJECTED,
                            submitted_value_masked=masked_value(submitted_value),
                            metadata={"submitted": True, "dikript_message": message},
                            review_note=message,
                        )
                        corper.nin_verification_status = CorperProfile.SensitiveStatus.REJECTED
                        corper.save(update_fields=["nin_verification_status", "updated_at"])
                    else:
                        returned_nin = _normalize_nin_value(
                            data.get("nin") or data.get("vNin") or data.get("VNin") or data.get("NIN")
                        )
                        if returned_nin and returned_nin != _normalize_nin_value(submitted_value):
                            review_note = "NIN does not match the NIN record."
                            attempt = VerificationAttempt.objects.create(
                                corper=corper,
                                verification_type=verification_type,
                                status=VerificationAttempt.Status.REJECTED,
                                submitted_value_masked=masked_value(submitted_value),
                                metadata={
                                    "submitted": True,
                                    "dikript_message": extract_dikript_message(payload),
                                    "returned_nin": returned_nin,
                                },
                                review_note=review_note,
                            )
                            corper.nin_verification_status = CorperProfile.SensitiveStatus.REJECTED
                            corper.save(update_fields=["nin_verification_status", "updated_at"])
                        else:
                            attempt = VerificationAttempt.objects.create(
                                corper=corper,
                                verification_type=verification_type,
                                status=VerificationAttempt.Status.APPROVED,
                                submitted_value_masked=masked_value(submitted_value),
                                metadata={
                                    "submitted": True,
                                    "dikript_message": extract_dikript_message(payload),
                                    "dikript_transaction_ref": payload.get("transactionRef"),
                                },
                            )
                            corper.nin_number = submitted_value
                            corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
                            corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
                            corper.save(
                                update_fields=[
                                    "nin_number",
                                    "nin_last4",
                                    "nin_lookup_hash",
                                    "nin_verification_status",
                                    "biodata_verification_status",
                                    "updated_at",
                                ]
                            )
                elif verification_type == VerificationAttempt.VerificationType.CALLUP:
                    attempt = VerificationAttempt.objects.create(
                        corper=corper,
                        verification_type=verification_type,
                        submitted_value_masked=masked_value(submitted_value),
                        metadata={"submitted": True},
                    )
                    corper.nysc_callup_number = submitted_value
                    corper.nysc_callup_document = document
                    corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.PENDING
                    corper.save(
                        update_fields=[
                            "nysc_callup_number",
                            "nysc_callup_document",
                            "nysc_callup_lookup_hash",
                            "nysc_callup_verification_status",
                            "updated_at",
                        ]
                    )
                elif verification_type == VerificationAttempt.VerificationType.STATE_CODE:
                    attempt = VerificationAttempt.objects.create(
                        corper=corper,
                        verification_type=verification_type,
                        submitted_value_masked=masked_value(submitted_value),
                        metadata={"submitted": True},
                    )
                    corper.nysc_state_code = submitted_value
                    corper.nysc_state_code_document = document
                    corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.PENDING
                    corper.save(
                        update_fields=[
                            "nysc_state_code",
                            "nysc_state_code_document",
                            "nysc_state_code_lookup_hash",
                            "nysc_state_code_verification_status",
                            "updated_at",
                        ]
                    )
                elif verification_type == VerificationAttempt.VerificationType.PROFILE:
                    attempt = VerificationAttempt.objects.create(
                        corper=corper,
                        verification_type=verification_type,
                        submitted_value_masked=masked_value(submitted_value),
                        metadata={"submitted": True},
                    )
                    corper.verification_status = CorperProfile.VerificationStatus.UNDER_REVIEW
                    corper.save(update_fields=["verification_status", "updated_at"])
                if verification_type in {
                    VerificationAttempt.VerificationType.CALLUP,
                    VerificationAttempt.VerificationType.STATE_CODE,
                }:
                    file_field = (
                        corper.nysc_callup_document
                        if verification_type == VerificationAttempt.VerificationType.CALLUP
                        else corper.nysc_state_code_document
                    )
                    attempt.metadata = {
                        **(attempt.metadata or {}),
                        "document_name": str(file_field.name).rsplit("/", 1)[-1],
                        "document_path": file_field.url,
                    }
                    attempt.save(update_fields=["metadata", "updated_at"])
        except IntegrityError as exc:
            logger.exception(
                "Verification submission failed due to an integrity error",
                extra={
                    "user_id": str(request.user.id),
                    "verification_type": verification_type,
                },
            )
            error_message = _resolve_persistence_error_message(exc) or "This record already exists."
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=submitted_value,
                error_message=error_message,
            )
            return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception(
                "Verification submission failed during persistence",
                extra={
                    "user_id": str(request.user.id),
                    "verification_type": verification_type,
                },
            )
            error_message = _resolve_persistence_error_message(exc)
            _record_failed_attempt(
                corper=corper,
                verification_type=verification_type,
                submitted_value=submitted_value,
                error_message=error_message or "Unable to submit verification right now. Please try again.",
            )
            return Response(
                {"detail": error_message or "Unable to submit verification right now. Please try again."},
                status=status.HTTP_400_BAD_REQUEST if error_message else status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        log_audit_event(
            actor=request.user,
            action="verification.submitted",
            target_type="verification_attempt",
            target_id=str(attempt.id),
            metadata={"verification_type": verification_type},
        )
        serialized_attempt = VerificationAttemptSerializer(attempt).data
        if attempt.status == VerificationAttempt.Status.REJECTED:
            return Response(
                {
                    "detail": attempt.review_note or "Verification failed.",
                    "attempt": serialized_attempt,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serialized_attempt, status=status.HTTP_201_CREATED)


class VerificationAttemptDetailAPIView(generics.RetrieveAPIView):
    serializer_class = VerificationAttemptSerializer

    def get_permissions(self):
        if self.request.user.role == "admin":
            return [IsAdminUserRole()]
        return [IsCorperUser()]

    def get_queryset(self):
        queryset = VerificationAttempt.objects.select_related(
            "corper",
            "corper__user",
            "reviewed_by",
        )
        if self.request.user.role == "admin":
            return queryset
        return queryset.filter(corper__user=self.request.user)


class VerificationReviewAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    def post(self, request, pk, *args, **kwargs):
        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = VerificationAttempt.objects.select_related("corper", "corper__user").get(pk=pk)
        attempt.status = serializer.validated_data["status"]
        attempt.review_note = serializer.validated_data.get("review_note", "")
        attempt.reviewed_by = request.user
        attempt.save(update_fields=["status", "review_note", "reviewed_by", "updated_at"])

        corper = attempt.corper
        mapped_status = (
            CorperProfile.SensitiveStatus.VERIFIED
            if attempt.status == VerificationAttempt.Status.APPROVED
            else CorperProfile.SensitiveStatus.REJECTED
        )
        fields_to_update = ["updated_at"]
        if attempt.verification_type == VerificationAttempt.VerificationType.NIN:
            corper.nin_verification_status = mapped_status
            fields_to_update.append("nin_verification_status")
            if attempt.status == VerificationAttempt.Status.APPROVED:
                corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
                fields_to_update.append("biodata_verification_status")
        elif attempt.verification_type == VerificationAttempt.VerificationType.BIODATA:
            corper.biodata_verification_status = mapped_status
            fields_to_update.append("biodata_verification_status")
        elif attempt.verification_type == VerificationAttempt.VerificationType.CALLUP:
            corper.nysc_callup_verification_status = mapped_status
            fields_to_update.append("nysc_callup_verification_status")
        elif attempt.verification_type == VerificationAttempt.VerificationType.STATE_CODE:
            corper.nysc_state_code_verification_status = mapped_status
            fields_to_update.append("nysc_state_code_verification_status")
        elif attempt.verification_type == VerificationAttempt.VerificationType.PROFILE:
            corper.verification_status = (
                CorperProfile.VerificationStatus.VERIFIED
                if attempt.status == VerificationAttempt.Status.APPROVED
                else CorperProfile.VerificationStatus.REJECTED
            )
            fields_to_update.append("verification_status")

        corper.save(update_fields=fields_to_update)
        create_notification(
            recipient=corper.user,
            notification_type=Notification.Type.PROFILE_VERIFICATION_UPDATE,
            title="Verification status updated",
            body=f"Your {attempt.verification_type} verification is now {attempt.status}.",
            data={"attempt_id": str(attempt.id), "status": attempt.status},
        )
        log_audit_event(
            actor=request.user,
            action="verification.reviewed",
            target_type="verification_attempt",
            target_id=str(attempt.id),
            metadata={"status": attempt.status},
        )
        return Response(VerificationAttemptSerializer(attempt).data)
