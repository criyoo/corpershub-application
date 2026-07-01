from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import APIException

from apps.common.validators import (
    normalize_mobile_number,
)
from apps.verification.models import DikriptVerificationCache

logger = logging.getLogger(__name__)


class DikriptVerificationUnavailable(APIException):
    status_code = 503
    default_detail = "Unable to verify the record right now. Try again later."
    default_code = "dikript_verification_unavailable"


def _dikript_key() -> str:
    return getattr(settings, "DIKRIPT_SECRET_KEY", "") or getattr(settings, "DIKRIPT_PUBLIC_KEY", "")


def _lookup_cache_timeout_seconds() -> int:
    return int(getattr(settings, "DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS", 60 * 60 * 24) or 60 * 60 * 24)


def _lookup_cache_cutoff():
    return timezone.now() - timedelta(seconds=_lookup_cache_timeout_seconds())


def _lookup_cache_key(verification_type: str, lookup_hash: str) -> str:
    return f"dikript_lookup:{verification_type}:{lookup_hash}"


def _lookup_hash(lookup_value: str) -> str:
    return hashlib.sha256(lookup_value.encode("utf-8")).hexdigest()


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    sanitized = json.loads(json.dumps(payload))
    data = sanitized.get("data")
    if isinstance(data, dict):
        data.pop("photo", None)
        data.pop("signature", None)
    return sanitized


def _payload_has_reusable_verification_data(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not payload.get("status"):
        return False
    data = payload.get("data")
    return isinstance(data, dict) and bool(data)


def dikript_get(path: str, query: dict[str, Any]) -> dict[str, Any]:
    base_url = (getattr(settings, "DIKRIPT_API_BASE_URL", "") or "").rstrip("/")
    api_key = _dikript_key()
    if not base_url or not api_key:
        logger.error(
            "Dikript verification is not configured.",
            extra={"has_base_url": bool(base_url), "has_api_key": bool(api_key)},
        )
        raise DikriptVerificationUnavailable()

    request = Request(
        url=f"{base_url}{path}?{urlencode(query)}",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=getattr(settings, "DIKRIPT_TIMEOUT_SECONDS", 10)) as response:
            return _decode_dikript_response(response.read())
    except HTTPError as exc:
        payload = _decode_dikript_response(exc.read(), allow_empty=True)
        message = extract_dikript_message(payload)
        if exc.code in {400, 404} and message:
            return payload
        logger.warning("Dikript verification failed with HTTP error.", extra={"status_code": exc.code, "path": path})
        raise DikriptVerificationUnavailable(detail=message or None) from exc
    except URLError as exc:
        logger.warning("Dikript verification failed with network error.", extra={"path": path})
        raise DikriptVerificationUnavailable() from exc


def dikript_lookup(
    *,
    verification_type: str,
    path: str,
    lookup_value: str,
    query: dict[str, Any],
) -> dict[str, Any]:
    base_url = (getattr(settings, "DIKRIPT_API_BASE_URL", "") or "").rstrip("/")
    api_key = _dikript_key()
    if not base_url or not api_key:
        logger.error(
            "Dikript verification is not configured.",
            extra={"has_base_url": bool(base_url), "has_api_key": bool(api_key)},
        )
        raise DikriptVerificationUnavailable()

    lookup_hash = _lookup_hash(lookup_value)
    cache_key = _lookup_cache_key(verification_type, lookup_hash)
    cache_model = DikriptVerificationCache.get_model(verification_type)
    cached_payload = cache.get(cache_key)
    if _payload_has_reusable_verification_data(cached_payload):
        return cached_payload

    db_payload = (
        cache_model.objects.filter(
            lookup_hash=lookup_hash,
            fetched_at__gte=_lookup_cache_cutoff(),
        )
        .values_list("payload", flat=True)
        .first()
    )
    if _payload_has_reusable_verification_data(db_payload):
        cache.set(cache_key, db_payload, timeout=_lookup_cache_timeout_seconds())
        return db_payload

    payload = _sanitize_payload(dikript_get(path, query))
    if _payload_has_reusable_verification_data(payload):
        cache_model.objects.update_or_create(
            lookup_hash=lookup_hash,
            defaults={"payload": payload},
        )
        cache.set(cache_key, payload, timeout=_lookup_cache_timeout_seconds())
    return payload


def extract_dikript_message(payload: dict[str, Any]) -> str:
    message = str(payload.get("message") or payload.get("error") or "").strip()
    return message


def _decode_dikript_response(raw_response: bytes, *, allow_empty: bool = False) -> dict[str, Any]:
    if not raw_response:
        if allow_empty:
            return {}
        logger.warning("Dikript verification returned an empty response body.")
        raise DikriptVerificationUnavailable()

    try:
        decoded = raw_response.decode("utf-8")
        return json.loads(decoded) if decoded else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Dikript verification returned invalid JSON.")
        raise DikriptVerificationUnavailable() from exc


def normalize_person_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().upper().split())


def normalize_free_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().upper().split())


def normalize_country_text(value: str | None) -> str:
    return normalize_free_text(value)


def normalize_phone_for_nin_match(value: str | None) -> str:
    normalized_value = str(value or "").strip()
    if not normalized_value:
        return ""

    if normalized_value.startswith("+234"):
        return f"+234{re.sub(r'\\D', '', normalized_value[4:])}"

    digits = re.sub(r"\D", "", normalize_mobile_number(normalized_value))
    if not digits:
        return ""
    if digits.startswith("234"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+234{digits[1:]}"
    return f"+{digits}" if normalized_value.startswith("+") else digits


def nin_phone_numbers_match(profile_value: str | None, api_value: str | None) -> bool:
    normalized_profile = normalize_phone_for_nin_match(profile_value)
    normalized_api = normalize_phone_for_nin_match(api_value)
    if not normalized_profile or not normalized_api:
        return False
    if normalized_profile == normalized_api:
        return True
    return normalized_profile.removeprefix("+234") == normalized_api.removeprefix("+234")


def parse_registration_date(value: str | None) -> date | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    parsed = parse_date(raw_value[:10])
    return parsed


def normalize_company_name_for_match(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\b(limited|ltd|plc|llc|incorporated|inc)\b", " ", normalized)
    return " ".join(normalized.split())


def company_names_match(profile_value: str | None, api_value: str | None) -> bool:
    left = normalize_company_name_for_match(profile_value)
    right = normalize_company_name_for_match(api_value)
    if not left or not right:
        return False
    if left == right or left in right or right in left:
        return True
    return SequenceMatcher(a=left, b=right).ratio() >= 0.8


def normalize_registration_digits(value: str | None) -> str:
    return re.sub(r"\D", "", str(value or ""))


def normalize_registration_lookup_value(value: str | None) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", normalized)


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes"}
