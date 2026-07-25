from __future__ import annotations

import base64
import hashlib
import hmac
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


class PremblyWebhookVerificationError(APIException):
    status_code = 401
    default_detail = "Invalid Prembly webhook signature."
    default_code = "prembly_webhook_verification_failed"


def _prembly_key() -> str:
    return str(getattr(settings, "PREMBLY_API_SECRET_KEY", "") or "").strip()


def _prembly_public_key() -> str:
    return str(getattr(settings, "PREMBLY_API_PUBLIC_KEY", "") or "").strip()


def _payload_bytes(raw_body: bytes | str) -> bytes:
    if isinstance(raw_body, bytes):
        return raw_body
    return str(raw_body or "").encode("utf-8")


def _header_value(headers: Any, name: str) -> str:
    if headers is None:
        return ""

    candidates = [
        name,
        name.lower(),
        name.upper(),
        name.title(),
        f"HTTP_{name.upper().replace('-', '_')}",
    ]
    for candidate in candidates:
        value = headers.get(candidate) if hasattr(headers, "get") else None
        if value not in (None, ""):
            return str(value).strip()

    if not hasattr(headers, "items"):
        return ""

    target = name.lower()
    for key, value in headers.items():
        normalized_key = str(key)
        if normalized_key.startswith("HTTP_"):
            normalized_key = normalized_key[5:]
        normalized_key = normalized_key.replace("_", "-").lower()
        if normalized_key == target and value not in (None, ""):
            return str(value).strip()
    return ""


def compute_prembly_webhook_signature(raw_body: bytes | str, *, public_key: str | None = None) -> str:
    signing_key = str(public_key if public_key is not None else _prembly_public_key()).strip()
    if not signing_key:
        logger.warning("Prembly webhook public key is not configured.")
        return ""
    expected_signature = hmac.new(
        signing_key.encode("utf-8"),
        msg=_payload_bytes(raw_body),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(expected_signature).decode("utf-8")


def verify_prembly_webhook_signature(*, raw_body: bytes | str, signature: str, public_key: str | None = None) -> bool:
    provided_signature = str(signature or "").strip()
    if not provided_signature:
        return False
    if provided_signature.lower().startswith("sha256="):
        provided_signature = provided_signature[7:].strip()
    try:
        provided_signature_bytes = provided_signature.encode("ascii")
    except UnicodeEncodeError:
        return False

    expected_signature = compute_prembly_webhook_signature(raw_body, public_key=public_key)
    return bool(expected_signature) and hmac.compare_digest(
        provided_signature_bytes,
        expected_signature.encode("ascii"),
    )


def mark_prembly_webhook_token_processed(token: str) -> bool:
    token_value = str(token or "").strip()
    if not token_value:
        return False
    token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    cache_key = f"prembly_webhook_token:{token_hash}"
    return cache.add(
        cache_key,
        True,
        timeout=getattr(settings, "PREMBLY_WEBHOOK_TOKEN_CACHE_SECONDS", 60 * 60 * 24 * 7),
    )


def validate_prembly_webhook_request(*, headers: Any, raw_body: bytes | str, track_token: bool = True) -> dict[str, Any]:
    signature = _header_value(headers, "x-prembly-signature")
    token = _header_value(headers, "token")

    if not signature or not token:
        raise PremblyWebhookVerificationError(detail="Missing Prembly webhook security headers.")
    if not verify_prembly_webhook_signature(raw_body=raw_body, signature=signature):
        raise PremblyWebhookVerificationError()

    return {
        "token": token,
        "already_processed": track_token and not mark_prembly_webhook_token_processed(token),
    }


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
        with urlopen(request, timeout=getattr(settings, "PREMBLY_TIMEOUT_SECONDS", 60)) as response:
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
