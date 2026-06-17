import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.verification.dikript import _lookup_hash, _lookup_cache_key, dikript_lookup
from apps.verification.models import DikriptVerificationCache, NINDikriptVerificationCache


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
    DIKRIPT_API_BASE_URL="https://api.dikript.com",
    DIKRIPT_NIN_API_URL="/dikript/verification/api/v1/getnin",
    DIKRIPT_SECRET_KEY="test-key",
    DIKRIPT_TIMEOUT_SECONDS=10,
)
class DikriptLookupTests(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.lookup_value = "91231161558"
        self.lookup_hash = _lookup_hash(self.lookup_value)
        self.cache_key = _lookup_cache_key(
            DikriptVerificationCache.VerificationType.NIN,
            self.lookup_hash,
        )

    def test_negative_database_cache_is_refreshed_from_live_lookup(self):
        NINDikriptVerificationCache.objects.create(
            lookup_hash=self.lookup_hash,
            payload={
                "status": False,
                "message": "No NIN record was found for this number.",
                "data": None,
            },
        )

        live_payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "firstName": "CHRISTIAN",
                "surname": "ALUYA",
                "nin": "91231161558",
            },
        }

        with patch("apps.verification.dikript.urlopen", return_value=_FakeHTTPResponse(live_payload)) as urlopen_mock:
            payload = dikript_lookup(
                verification_type=DikriptVerificationCache.VerificationType.NIN,
                path="/dikript/verification/api/v1/getnin",
                lookup_value=self.lookup_value,
                query={"nin": self.lookup_value},
            )

        self.assertEqual(payload["data"]["nin"], "91231161558")
        self.assertEqual(urlopen_mock.call_count, 1)
        cached_record = NINDikriptVerificationCache.objects.get(
            lookup_hash=self.lookup_hash,
        )
        self.assertTrue(cached_record.payload["status"])
        self.assertEqual(cached_record.payload["data"]["nin"], "91231161558")

    def test_negative_runtime_cache_is_refreshed_from_live_lookup(self):
        cache.set(
            self.cache_key,
            {
                "status": False,
                "message": "No NIN record was found for this number.",
                "data": None,
            },
            timeout=3600,
        )

        live_payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "firstName": "CHRISTIAN",
                "surname": "ALUYA",
                "nin": "91231161558",
            },
        }

        with patch("apps.verification.dikript.urlopen", return_value=_FakeHTTPResponse(live_payload)) as urlopen_mock:
            payload = dikript_lookup(
                verification_type=DikriptVerificationCache.VerificationType.NIN,
                path="/dikript/verification/api/v1/getnin",
                lookup_value=self.lookup_value,
                query={"nin": self.lookup_value},
            )

        self.assertEqual(payload["data"]["nin"], "91231161558")
        self.assertEqual(urlopen_mock.call_count, 1)
        refreshed_cache_payload = cache.get(self.cache_key)
        self.assertTrue(refreshed_cache_payload["status"])
        self.assertEqual(refreshed_cache_payload["data"]["nin"], "91231161558")

    def test_failed_lookup_response_is_not_persisted_in_database(self):
        failed_payload = {
            "status": False,
            "message": "No NIN record was found for this number.",
            "data": None,
        }

        with patch("apps.verification.dikript.urlopen", return_value=_FakeHTTPResponse(failed_payload)) as urlopen_mock:
            payload = dikript_lookup(
                verification_type=DikriptVerificationCache.VerificationType.NIN,
                path="/dikript/verification/api/v1/getnin",
                lookup_value=self.lookup_value,
                query={"nin": self.lookup_value},
            )

        self.assertFalse(payload["status"])
        self.assertEqual(urlopen_mock.call_count, 1)
        self.assertFalse(
            NINDikriptVerificationCache.objects.filter(
                lookup_hash=self.lookup_hash,
            ).exists()
        )
