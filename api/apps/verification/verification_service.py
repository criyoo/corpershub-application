from __future__ import annotations

import re
from typing import Any

from django.conf import settings
from rest_framework.exceptions import APIException

from apps.verification.models import DikriptVerificationCache


class VerificationProviderUnavailable(APIException):
    status_code = 503
    default_detail = "Verification provider is not configured."
    default_code = "verification_provider_unavailable"


def active_verification_provider() -> str:
    return str(getattr(settings, "VERIFICATION_SERVICE", "prembly") or "prembly").strip().lower()


def _split_cac_registration_number(value: str) -> tuple[str, str]:
    normalized = str(value or "").strip().upper()
    match = re.match(r"^(LLP|RC|BN|IT|LP)(.+)$", re.sub(r"[^A-Z0-9]+", "", normalized))
    if match:
        company_type, number = match.groups()
        return number, company_type
    return re.sub(r"\D", "", normalized), str(getattr(settings, "PREMBLY_CAC_COMPANY_TYPE", "RC") or "RC").upper()


def _prembly_lookup_kwargs(
    *,
    verification_type: str,
    lookup_value: str,
    query: dict[str, Any] | None,
) -> dict[str, Any]:
    query = query or {}
    if verification_type == DikriptVerificationCache.VerificationType.NIN:
        nin_number = str(query.get("nin") or lookup_value or "").strip()
        return {
            "verification_type": verification_type,
            "path": settings.PREMBLY_NIN_API_URL,
            "lookup_value": nin_number,
            "body": {"number_nin": nin_number},
        }

    if verification_type == DikriptVerificationCache.VerificationType.CAC:
        registration_number = str(query.get("regNumber") or lookup_value or "").strip()
        rc_number, company_type = _split_cac_registration_number(registration_number)
        body = {
            "rc_number": rc_number,
            "company_type": company_type,
        }
        company_name = str(query.get("company_name") or "").strip()
        if company_name:
            body["company_name"] = company_name
        return {
            "verification_type": verification_type,
            "path": settings.PREMBLY_CAC_API_URL,
            "lookup_value": f"{company_type}:{rc_number}",
            "body": body,
        }

    raise VerificationProviderUnavailable(detail=f"Unsupported verification type: {verification_type}")


def verification_lookup(
    *,
    verification_type: str,
    path: str,
    lookup_value: str,
    query: dict[str, Any],
) -> dict[str, Any]:
    provider = active_verification_provider()
    if provider == "prembly":
        from apps.verification.prembly_verification import prembly_lookup

        return prembly_lookup(**_prembly_lookup_kwargs(
            verification_type=verification_type,
            lookup_value=lookup_value,
            query=query,
        ))

    if provider == "dikript":
        from apps.verification.dikript import dikript_lookup

        return dikript_lookup(
            verification_type=verification_type,
            path=path,
            lookup_value=lookup_value,
            query=query,
        )

    raise VerificationProviderUnavailable(detail=f"Unsupported verification provider: {provider}")


def extract_verification_message(payload: dict[str, Any]) -> str:
    return str(payload.get("message") or payload.get("detail") or payload.get("error") or "").strip()
