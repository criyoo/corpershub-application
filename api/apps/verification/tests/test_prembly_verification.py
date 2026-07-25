import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.verification.models import DikriptVerificationCache, NINDikriptVerificationCache
from apps.verification.prembly_verification import _lookup_hash, prembly_lookup
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


@override_settings(
    VERIFICATION_SERVICE="prembly",
    PREMBLY_API_BASE_URL="https://api.prembly.com",
    PREMBLY_NIN_API_URL="/verification/vnin",
    PREMBLY_CAC_API_URL="/verification/cac",
    PREMBLY_API_KEY="test-key",
    PREMBLY_TIMEOUT_SECONDS=10,
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
