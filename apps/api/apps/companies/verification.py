from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import normalize_company_registration_number
from apps.verification.dikript import (
    company_names_match,
    dikript_lookup,
    extract_dikript_message,
    is_truthy,
    normalize_registration_digits,
    normalize_registration_lookup_value,
    parse_registration_date,
)
from apps.verification.models import DikriptVerificationCache


def _registration_dates_match_with_tolerance(*, expected_value, returned_value, tolerance_days: int = 2) -> bool:
    if expected_value is None or returned_value is None:
        return False
    return abs(expected_value - returned_value) <= timedelta(days=tolerance_days)


def verify_company_profile_or_raise(company: CompanyProfile) -> dict:
    normalized_registration_number = normalize_company_registration_number(
        company.company_registration_number
    )
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

    if not is_truthy(data.get("registrationApproved")):
        raise ValidationError(
            {"company_registration_number": "CAC has not approved this registration record."}
        )

    expected_digits = normalize_registration_digits(normalized_registration_number)
    returned_digits = normalize_registration_digits(data.get("rcNumber"))
    if not expected_digits or expected_digits != returned_digits:
        raise ValidationError({"company_registration_number": "The RC number does not match the CAC record."})

    if not company_names_match(company.company_name, data.get("companyName")):
        raise ValidationError({"company_name": "The company name does not match the CAC record."})

    company_registration_date = company.company_registration_date
    returned_registration_date = parse_registration_date(data.get("registrationDate"))
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
