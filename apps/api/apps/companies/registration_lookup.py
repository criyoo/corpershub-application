from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

from apps.verification.dikript import (
    dikript_lookup,
    extract_dikript_message,
    is_truthy,
    normalize_registration_digits,
    normalize_registration_lookup_value,
)
from apps.verification.models import DikriptVerificationCache

logger = logging.getLogger(__name__)

ALLOWED_COMPANY_REGISTRATION_PREFIXES = ("LLP", "RC", "BN", "IT", "LP")
COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE = (
    "Enter a valid company registration number in the format RC12345, BN12345, "
    "IT12345, LP12345, or LLP12345 without any spaces."
)
COMPANY_REGISTRATION_NUMBER_PATTERN = re.compile(
    rf"^(?:{'|'.join(ALLOWED_COMPANY_REGISTRATION_PREFIXES)})\d{{5,10}}$"
)
COMPANY_REGISTRATION_NUMBER_COERCION_PATTERN = re.compile(
    rf"^({'|'.join(ALLOWED_COMPANY_REGISTRATION_PREFIXES)})\s*(?:-\s*|\s+)?(\d{{5,10}})$"
)


class CompanyRegistrationLookupUnavailable(APIException):
    status_code = 503
    default_detail = "Unable to verify the company registration number right now. Try again later."
    default_code = "company_registration_lookup_unavailable"


@dataclass(frozen=True)
class CompanyRegistrationLookupResult:
    company_name: str
    company_registration_number: str
    company_address: str
    company_status: str
    registration_date: str
    company_type: str
    is_active: bool

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "company_registration_number": self.company_registration_number,
            "company_address": self.company_address,
            "company_status": self.company_status,
            "registration_date": self.registration_date,
            "company_type": self.company_type,
            "is_active": self.is_active,
        }


def normalize_company_registration_number(value: str) -> str:
    normalized = (value or "").strip().upper()
    if not normalized:
        return ""

    match = COMPANY_REGISTRATION_NUMBER_COERCION_PATTERN.fullmatch(normalized)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return re.sub(r"\s+", "", normalized)


def coerce_company_registration_number(value: str) -> str:
    return normalize_company_registration_number(value)


def is_valid_company_registration_number(value: str) -> bool:
    normalized = normalize_company_registration_number(value)
    return bool(COMPANY_REGISTRATION_NUMBER_PATTERN.fullmatch(normalized))


def resolve_company_registration_active_status(raw_is_active: Any, company_status: str) -> bool:
    normalized_status = str(company_status or "").strip().upper()
    return is_truthy(raw_is_active) or normalized_status == "ACTIVE"


def lookup_company_registration_number(
    company_registration_number: str,
) -> CompanyRegistrationLookupResult:
    normalized_registration_number = normalize_company_registration_number(company_registration_number)
    if not normalized_registration_number:
        raise ValidationError(
            {"company_registration_number": "Company registration number is required."}
        )
    if not is_valid_company_registration_number(normalized_registration_number):
        raise ValidationError(
            {"company_registration_number": COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE}
        )

    try:
        normalized_lookup_value = normalize_registration_lookup_value(normalized_registration_number)
        payload = dikript_lookup(
            verification_type=DikriptVerificationCache.VerificationType.CAC,
            path=settings.DIKRIPT_CAC_API_URL,
            lookup_value=normalized_lookup_value,
            query={"regNumber": normalized_lookup_value},
        )
    except APIException as exc:
        if isinstance(exc, ValidationError):
            raise
        raise CompanyRegistrationLookupUnavailable(detail=getattr(exc, "detail", None)) from exc

    data = payload.get("data") or {}
    if not payload.get("status") or not isinstance(data, dict) or not data:
        raise ValidationError(
            {"company_registration_number": _build_lookup_failure_message(payload)}
        )

    company_name = str(data.get("companyName") or "").strip()
    company_status = "APPROVED" if is_truthy(data.get("registrationApproved")) else "PENDING"
    company_registration_number = coerce_company_registration_number(
        f"RC {normalize_registration_digits(data.get('rcNumber') or normalized_registration_number)}"
    )
    if not company_name or not company_registration_number:
        logger.warning(
            "Company registration lookup returned incomplete data.",
            extra={"company_registration_number": normalized_registration_number},
        )
        raise CompanyRegistrationLookupUnavailable()
    if not is_valid_company_registration_number(company_registration_number):
        logger.warning(
            "Company registration lookup returned an invalid registration number format.",
            extra={
                "requested_company_registration_number": normalized_registration_number,
                "returned_company_registration_number": company_registration_number,
            },
        )
        raise CompanyRegistrationLookupUnavailable()

    is_active = resolve_company_registration_active_status(data.get("registrationApproved"), company_status)
    if not is_active:
        raise ValidationError(
            {
                "company_registration_number": (
                    "This company registration is not approved by CAC yet."
                )
            }
        )

    return CompanyRegistrationLookupResult(
        company_name=company_name,
        company_registration_number=company_registration_number,
        company_address=str(data.get("address") or data.get("headOfficeAddress") or "").strip(),
        company_status=company_status,
        registration_date=str(data.get("registrationDate") or "").strip(),
        company_type=str(data.get("companyType") or data.get("classification") or "").strip(),
        is_active=is_active,
    )


def _decode_lookup_response(raw_response: bytes, *, allow_empty: bool = False) -> dict[str, Any]:
    if not raw_response:
        if allow_empty:
            return {}
        logger.warning("Company registration lookup returned an empty response body.")
        raise CompanyRegistrationLookupUnavailable()

    try:
        decoded = raw_response.decode("utf-8")
        return json.loads(decoded) if decoded else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Company registration lookup returned invalid JSON.")
        raise CompanyRegistrationLookupUnavailable() from exc


def _build_lookup_failure_message(payload: dict[str, Any]) -> str:
    message = extract_dikript_message(payload).lower()
    if "invalid" in message:
        return COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE
    return "No company was found for this registration number."
