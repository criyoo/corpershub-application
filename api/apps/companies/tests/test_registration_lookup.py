import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.companies.registration_lookup import (
    COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
    CompanyRegistrationLookupUnavailable,
    coerce_company_registration_number,
    is_valid_company_registration_number,
    lookup_company_registration_number,
    normalize_company_registration_number,
    resolve_company_registration_active_status,
)


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
    DIKRIPT_CAC_API_URL="/dikript/verification/api/v1/getcacbasic",
    DIKRIPT_SECRET_KEY="test-key",
    DIKRIPT_TIMEOUT_SECONDS=10,
)
class CompanyRegistrationLookupTests(SimpleTestCase):
    def test_normalize_company_registration_number(self):
        self.assertEqual(normalize_company_registration_number("rc 1754689"), "RC1754689")
        self.assertEqual(normalize_company_registration_number("RC 1754689"), "RC1754689")
        self.assertEqual(normalize_company_registration_number("llp 12345"), "LLP12345")

    def test_coerce_company_registration_number(self):
        self.assertEqual(coerce_company_registration_number("rc-1754689"), "RC1754689")
        self.assertEqual(coerce_company_registration_number("RC - 1754689"), "RC1754689")
        self.assertEqual(coerce_company_registration_number("LLP 12345"), "LLP12345")

    def test_is_valid_company_registration_number(self):
        self.assertTrue(is_valid_company_registration_number("RC 1754689"))
        self.assertTrue(is_valid_company_registration_number("LLP 12345"))
        self.assertFalse(is_valid_company_registration_number("ABC 1754689"))
        self.assertFalse(is_valid_company_registration_number("RC 1234"))
        self.assertFalse(is_valid_company_registration_number("RC 12345678901"))
        self.assertTrue(is_valid_company_registration_number("RC-1754689"))
        self.assertTrue(is_valid_company_registration_number("RC  1754689"))

    def test_resolve_company_registration_active_status(self):
        self.assertTrue(resolve_company_registration_active_status(True, "ACTIVE"))
        self.assertFalse(
            resolve_company_registration_active_status(None, "INACTIVE (Visit CAC and update your status)")
        )
        self.assertTrue(resolve_company_registration_active_status(None, "ACTIVE"))

    def test_lookup_company_registration_number_returns_company_details(self):
        payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "companyName": "RUTOB LIMITED",
                "rcNumber": "1754689",
                "address": "IGBOGENE SCHOOL ROAD, ,",
                "registrationApproved": True,
                "registrationDate": "2021-02-09T00:00:00.000Z",
                "companyType": "company",
            },
        }

        with patch(
            "apps.companies.registration_lookup.dikript_lookup",
            return_value=payload,
        ) as lookup_mock:
            company = lookup_company_registration_number("RC 1754689")

        self.assertEqual(lookup_mock.call_args.kwargs["lookup_value"], "RC1754689")
        self.assertEqual(lookup_mock.call_args.kwargs["query"], {"regNumber": "RC1754689"})
        self.assertEqual(company.company_name, "RUTOB LIMITED")
        self.assertEqual(company.company_registration_number, "RC1754689")
        self.assertEqual(company.company_address, "IGBOGENE SCHOOL ROAD, ,")
        self.assertEqual(company.company_status, "APPROVED")
        self.assertEqual(company.company_type, "company")
        self.assertTrue(company.is_active)

    def test_lookup_company_registration_number_rejects_inactive_companies(self):
        payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "companyName": "RUTOB LIMITED",
                "rcNumber": "1754689",
                "address": "IGBOGENE SCHOOL ROAD, ,",
                "registrationApproved": False,
                "registrationDate": "2021-02-09T00:00:00.000Z",
                "companyType": "company",
            },
        }

        with patch(
            "apps.companies.registration_lookup.dikript_lookup",
            return_value=payload,
        ):
            with self.assertRaises(ValidationError) as exc:
                lookup_company_registration_number("RC 1754689")

        self.assertEqual(
            str(exc.exception.detail["company_registration_number"]),
            "This company registration is not approved by CAC yet.",
        )

    def test_lookup_company_registration_number_rejects_unknown_numbers(self):
        payload = {
            "status": False,
            "message": "No company was found for this registration number.",
            "data": None,
        }

        with patch(
            "apps.companies.registration_lookup.dikript_lookup",
            return_value=payload,
        ):
            with self.assertRaises(ValidationError) as exc:
                lookup_company_registration_number("RC 0000000")

        self.assertEqual(
            str(exc.exception.detail["company_registration_number"]),
            "No company was found for this registration number.",
        )

    def test_lookup_company_registration_number_rejects_invalid_format(self):
        with self.assertRaises(ValidationError) as exc:
            lookup_company_registration_number("XYZ 1234")

        self.assertEqual(
            str(exc.exception.detail["company_registration_number"]),
            COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
        )

    def test_lookup_company_registration_number_accepts_hyphenated_user_input(self):
        payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "companyName": "RUTOB LIMITED",
                "rcNumber": "1754689",
                "address": "IGBOGENE SCHOOL ROAD, ,",
                "registrationApproved": True,
                "registrationDate": "2021-02-09T00:00:00.000Z",
                "companyType": "company",
            },
        }

        with patch(
            "apps.companies.registration_lookup.dikript_lookup",
            return_value=payload,
        ) as lookup_mock:
            company = lookup_company_registration_number("RC-1754689")

        self.assertEqual(lookup_mock.call_args.kwargs["lookup_value"], "RC1754689")
        self.assertEqual(lookup_mock.call_args.kwargs["query"], {"regNumber": "RC1754689"})
        self.assertEqual(company.company_registration_number, "RC1754689")

    @override_settings(DIKRIPT_SECRET_KEY="")
    def test_lookup_company_registration_number_requires_configuration(self):
        with self.assertRaises(CompanyRegistrationLookupUnavailable):
            lookup_company_registration_number("RC 1754689")
