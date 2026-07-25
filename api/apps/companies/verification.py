from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import normalize_company_registration_number
from apps.verification.dikript import (
    company_names_match,
    is_truthy,
    normalize_registration_digits,
    normalize_registration_lookup_value,
    parse_registration_date,
)
from apps.verification.models import DikriptVerificationCache
from apps.verification.verification_service import (
    extract_verification_message as extract_dikript_message,
    verification_lookup as dikript_lookup,
)


def _registration_dates_match_with_tolerance(*, expected_value, returned_value, tolerance_days: int = 2) -> bool:
    if expected_value is None or returned_value is None:
        return False
    return abs(expected_value - returned_value) <= timedelta(days=tolerance_days)


def _first_present(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return ""


def _cac_registration_is_active(data: dict) -> bool:
    registration_approved = data.get("registrationApproved")
    if registration_approved is not None:
        return is_truthy(registration_approved)
    return str(_first_present(data, "company_status", "status") or "").strip().upper() == "ACTIVE"


def verify_company_profile_or_raise(company: CompanyProfile) -> dict:
    normalized_registration_number = normalize_company_registration_number(company.company_registration_number)
    normalized_lookup_value = normalize_registration_lookup_value(normalized_registration_number)
    payload = dikript_lookup(
        verification_type=DikriptVerificationCache.VerificationType.CAC,
        path=settings.DIKRIPT_CAC_API_URL,
        lookup_value=normalized_lookup_value,
        query={"regNumber": normalized_lookup_value},
    )
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    if not payload.get("status") or not data:
        raise ValidationError(
            {
                "company_registration_number": (
                    extract_dikript_message(payload) or "No CAC record was found for this RC number."
                )
            }
        )

    if not _cac_registration_is_active(data):
        raise ValidationError({"company_registration_number": "CAC has not approved this registration record."})

    expected_digits = normalize_registration_digits(normalized_registration_number)
    returned_digits = normalize_registration_digits(_first_present(data, "rcNumber", "rc_number", "number"))
    if not expected_digits or expected_digits != returned_digits:
        raise ValidationError({"company_registration_number": "The RC number does not match the CAC record."})

    if not company_names_match(company.company_name, _first_present(data, "companyName", "company_name")):
        raise ValidationError({"company_name": "The company name does not match the CAC record."})

    company_registration_date = company.company_registration_date
    returned_registration_date = parse_registration_date(_first_present(data, "registrationDate", "date_of_registration"))
    if company_registration_date and not returned_registration_date:
        raise ValidationError(
            {"company_registration_date": "The company registration date could not be verified against CAC."}
        )
    if company_registration_date and not _registration_dates_match_with_tolerance(
        expected_value=company_registration_date,
        returned_value=returned_registration_date,
    ):
        raise ValidationError(
            {"company_registration_date": "The company registration date does not match the CAC record."}
        )

    return data
