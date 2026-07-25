import base64
import hashlib
import hmac
import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.verification.models import DikriptVerificationCache, NINDikriptVerificationCache
from apps.verification.prembly_verification import (
    PremblyVerificationUnavailable,
    PremblyWebhookVerificationError,
    _lookup_hash,
    prembly_lookup,
    validate_prembly_webhook_request,
    verify_prembly_webhook_signature,
)
from apps.verification.verification_service import verification_lookup


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class PremblyWebhookSecurityTests(TestCase):
    def _signature(self, raw_body: bytes, public_key: str) -> str:
        digest = hmac.new(public_key.encode("utf-8"), raw_body, hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    @override_settings(PREMBLY_API_PUBLIC_KEY="test-prembly-public-key")
    def test_prembly_webhook_signature_verifies_raw_body(self):
        raw_body = b'{"status":"completed","data":{"session_id":"123"}}'
        signature = self._signature(raw_body, "test-prembly-public-key")

        self.assertTrue(verify_prembly_webhook_signature(raw_body=raw_body, signature=signature))
        self.assertFalse(verify_prembly_webhook_signature(raw_body=raw_body + b" ", signature=signature))

    @override_settings(PREMBLY_API_PUBLIC_KEY="")
    def test_prembly_webhook_signature_rejects_missing_public_key(self):
        raw_body = b'{"status":"completed"}'
        signature = self._signature(raw_body, "test-prembly-public-key")

        with self.assertLogs("apps.verification.prembly_verification", level="WARNING"):
            self.assertFalse(verify_prembly_webhook_signature(raw_body=raw_body, signature=signature))

    @override_settings(PREMBLY_API_PUBLIC_KEY="test-prembly-public-key", PREMBLY_WEBHOOK_TOKEN_CACHE_SECONDS=60)
    def test_prembly_webhook_request_requires_signature_and_tracks_token(self):
        raw_body = b'{"status":"completed","data":{"session_id":"123"}}'
        token = "prembly-token-123"
        cache.delete(f"prembly_webhook_token:{hashlib.sha256(token.encode('utf-8')).hexdigest()}")
        headers = {
            "HTTP_X_PREMBLY_SIGNATURE": self._signature(raw_body, "test-prembly-public-key"),
            "HTTP_TOKEN": token,
        }

        validation = validate_prembly_webhook_request(headers=headers, raw_body=raw_body)
        duplicate_validation = validate_prembly_webhook_request(headers=headers, raw_body=raw_body)

        self.assertEqual(validation["token"], token)
        self.assertFalse(validation["already_processed"])
        self.assertTrue(duplicate_validation["already_processed"])

    @override_settings(PREMBLY_API_PUBLIC_KEY="test-prembly-public-key")
    def test_prembly_webhook_request_rejects_missing_or_invalid_security_headers(self):
        raw_body = b'{"status":"completed"}'

        with self.assertRaises(PremblyWebhookVerificationError):
            validate_prembly_webhook_request(headers={}, raw_body=raw_body)
        with self.assertRaises(PremblyWebhookVerificationError):
            validate_prembly_webhook_request(
                headers={
                    "x-prembly-signature": self._signature(raw_body, "test-prembly-public-key"),
                    "token": "token-1",
                },
                raw_body=b'{"status":"tampered"}',
            )


@override_settings(
    VERIFICATION_SERVICE="prembly",
    PREMBLY_API_BASE_URL="https://api.prembly.com",
    PREMBLY_NIN_API_URL="/verification/vnin",
    PREMBLY_CAC_API_URL="/verification/cac",
    PREMBLY_API_SECRET_KEY="test-key",
    PREMBLY_API_PUBLIC_KEY='test-public-key',
    PREMBLY_TIMEOUT_SECONDS=60,
    PREMBLY_LOOKUP_CACHE_TIMEOUT_SECONDS=86400,
)
class PremblyLookupTests(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_prembly_lookup_posts_and_caches_sanitized_payload(self):
        payload = {
            "status": True,
            "response_code": "00",
            "message": "National Identity Number (NIN) verification successful",
            "data": {
                "firstname": "CHRISTIAN",
                "surname": "ALUYA",
                "nin": "91231161558",
                "photo": "base64-photo",
                "signature": "base64-signature",
            },
            "verification_status": "verified",
        }

        with patch("apps.verification.prembly_verification.urlopen", return_value=_FakeHTTPResponse(payload)) as urlopen_mock:
            response = prembly_lookup(
                verification_type=DikriptVerificationCache.VerificationType.NIN,
                path="/verification/vnin",
                lookup_value="91231161558",
                body={"number_nin": "91231161558"},
            )

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.prembly.com/verification/vnin")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"number_nin": "91231161558"})
        self.assertNotIn("photo", response["data"])
        self.assertNotIn("signature", response["data"])

        lookup_hash = _lookup_hash(DikriptVerificationCache.VerificationType.NIN, "91231161558")
        cached_record = NINDikriptVerificationCache.objects.get(lookup_hash=lookup_hash)
        self.assertNotIn("photo", cached_record.payload["data"])
        self.assertNotIn("signature", cached_record.payload["data"])

    def test_verification_lookup_builds_prembly_cac_request(self):
        with patch("apps.verification.prembly_verification.prembly_lookup", return_value={"status": False}) as lookup_mock:
            verification_lookup(
                verification_type=DikriptVerificationCache.VerificationType.CAC,
                path="/ignored",
                lookup_value="RC9629888",
                query={"regNumber": "RC9629888"},
            )

        self.assertEqual(lookup_mock.call_args.kwargs["path"], "/verification/cac")
        self.assertEqual(lookup_mock.call_args.kwargs["lookup_value"], "RC:9629888")
        self.assertEqual(
            lookup_mock.call_args.kwargs["body"],
            {
                "rc_number": "9629888",
                "company_type": "RC",
            },
        )

    @override_settings(
        DIKRIPT_API_BASE_URL="https://api.dikript.com",
        DIKRIPT_NIN_API_URL="/dikript/verification/api/v1/getnin",
        DIKRIPT_SECRET_KEY="fallback-key",
        VERIFICATION_FALLBACK_SERVICE="dikript",
    )
    def test_verification_lookup_falls_back_to_dikript_when_prembly_is_unavailable(self):
        fallback_payload = {
            "status": True,
            "data": {"nin": "91231161558"},
        }

        with (
            patch(
                "apps.verification.prembly_verification.prembly_lookup",
                side_effect=PremblyVerificationUnavailable(),
            ),
            patch(
                "apps.verification.dikript.dikript_lookup",
                return_value=fallback_payload,
            ) as dikript_lookup_mock,
        ):
            response = verification_lookup(
                verification_type=DikriptVerificationCache.VerificationType.NIN,
                path="/dikript/verification/api/v1/getnin",
                lookup_value="91231161558",
                query={"nin": "91231161558"},
            )

        self.assertEqual(response, fallback_payload)
        self.assertEqual(
            dikript_lookup_mock.call_args.kwargs["path"],
            "/dikript/verification/api/v1/getnin",
        )
        self.assertEqual(dikript_lookup_mock.call_args.kwargs["query"], {"nin": "91231161558"})
