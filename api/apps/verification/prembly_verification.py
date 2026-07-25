from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.verification.models import DikriptVerificationCache

logger = logging.getLogger(__name__)


class PremblyVerificationUnavailable(APIException):
    status_code = 503
    default_detail = "Unable to verify the record right now. Try again later."
    default_code = "prembly_verification_unavailable"


def _prembly_key() -> str:
    return getattr(settings, "PREMBLY_API_KEY", "")


def _lookup_cache_timeout_seconds() -> int:
    return int(getattr(settings, "PREMBLY_LOOKUP_CACHE_TIMEOUT_SECONDS", 60 * 60 * 24) or 60 * 60 * 24)


def _lookup_cache_cutoff():
    return timezone.now() - timedelta(seconds=_lookup_cache_timeout_seconds())


def _lookup_hash(verification_type: str, lookup_value: str) -> str:
    return hashlib.sha256(f"prembly:{verification_type}:{lookup_value}".encode("utf-8")).hexdigest()


def _lookup_cache_key(verification_type: str, lookup_hash: str) -> str:
    return f"prembly_lookup:{verification_type}:{lookup_hash}"


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in {"photo", "signature", "base64image", "image"}:
                continue
            sanitized[key] = _sanitize_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    return value


def _payload_verified(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or payload.get("status") is not True:
        return False

    response_code = str(payload.get("response_code") or payload.get("code") or "").strip()
    if response_code and response_code not in {"00", "200"}:
        return False

    verification_status = str(payload.get("verification_status") or "").strip().lower()
    if verification_status and verification_status != "verified":
        return False

    verification = payload.get("verification")
    if isinstance(verification, dict):
        status = str(verification.get("status") or "").strip().upper()
        if status and status != "VERIFIED":
            return False

    return True


def _payload_has_reusable_verification_data(payload: dict[str, Any]) -> bool:
    if not _payload_verified(payload):
        return False
    data = payload.get("data")
    return isinstance(data, (dict, list)) and bool(data)


def extract_prembly_message(payload: dict[str, Any]) -> str:
    return str(payload.get("message") or payload.get("detail") or payload.get("error") or "").strip()


def _decode_prembly_response(raw_response: bytes, *, allow_empty: bool = False) -> dict[str, Any]:
    if not raw_response:
        if allow_empty:
            return {}
        logger.warning("Prembly verification returned an empty response body.")
        raise PremblyVerificationUnavailable()

    try:
        decoded = raw_response.decode("utf-8")
        payload = json.loads(decoded) if decoded else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Prembly verification returned invalid JSON.")
        raise PremblyVerificationUnavailable() from exc

    return payload if isinstance(payload, dict) else {}


def prembly_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    base_url = (getattr(settings, "PREMBLY_API_BASE_URL", "") or "").rstrip("/")
    api_key = _prembly_key()
    if not base_url or not api_key:
        logger.error(
            "Prembly verification is not configured.",
            extra={"has_base_url": bool(base_url), "has_api_key": bool(api_key)},
        )
        raise PremblyVerificationUnavailable()

    request = Request(
        url=f"{base_url}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=getattr(settings, "PREMBLY_TIMEOUT_SECONDS", 10)) as response:
            return _decode_prembly_response(response.read())
    except HTTPError as exc:
        payload = _decode_prembly_response(exc.read(), allow_empty=True)
        message = extract_prembly_message(payload)
        if exc.code in {400, 404, 422} and message:
            return payload
        logger.warning("Prembly verification failed with HTTP error.", extra={"status_code": exc.code, "path": path})
        raise PremblyVerificationUnavailable(detail=message or None) from exc
    except URLError as exc:
        logger.warning("Prembly verification failed with network error.", extra={"path": path})
        raise PremblyVerificationUnavailable() from exc


def prembly_lookup(
    *,
    verification_type: str,
    path: str,
    lookup_value: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    base_url = (getattr(settings, "PREMBLY_API_BASE_URL", "") or "").rstrip("/")
    api_key = _prembly_key()
    if not base_url or not api_key:
        logger.error(
            "Prembly verification is not configured.",
            extra={"has_base_url": bool(base_url), "has_api_key": bool(api_key)},
        )
        raise PremblyVerificationUnavailable()

    lookup_hash = _lookup_hash(verification_type, lookup_value)
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

    payload = _sanitize_payload(prembly_post(path, body))
    if _payload_has_reusable_verification_data(payload):
        cache_model.objects.update_or_create(
            lookup_hash=lookup_hash,
            defaults={"payload": payload},
        )
        cache.set(cache_key, payload, timeout=_lookup_cache_timeout_seconds())
    return payload
