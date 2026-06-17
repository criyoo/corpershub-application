import shutil
import tempfile
from datetime import date
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.legal import COMPANY_LEGAL_DOCUMENT_SLUGS
from apps.companies.models import CompanyProfile
from apps.companies.services import ensure_company_profile
from apps.companies.verification import verify_company_profile_or_raise


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class CompanyVerificationFlowTests(APITestCase):
    def setUp(self):
        self.temp_media_dir = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self.temp_media_dir)
        self.override_media.enable()
        self.company_user = User.objects.create_user(
            email="owner@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.admin_user = User.objects.create_user(
            email="admin@corpershub.ng",
            password="AdminPass123!",
            role="admin",
            email_verified=True,
            is_staff=True,
        )
        self.company = ensure_company_profile(self.company_user)

    def tearDown(self):
        self.override_media.disable()
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)
        super().tearDown()

    def _cac_payload(self, **overrides):
        data = {
            "companyName": "TCONNECT TECHNOLOGIES LIMITED",
            "classification": "COMPANY",
            "rcNumber": "9463122",
            "registrationApproved": True,
            "active": False,
            "natureOfBusinessName": "General Merchandise ",
            "companyType": "COMPANY",
            "registrationDate": "2026-04-02T23:30:53.626Z",
            "state": "Kano",
            "lga": None,
            "city": "Kano",
            "address": None,
            "registrationEmail": None,
            "businessCommencementDate": None,
            "headOfficeAddress": None,
            "branchAddress": None,
        }
        data.update(overrides)
        return {
            "status": True,
            "message": "Successful",
            "code": "200",
            "apiVersion": "v1",
            "transactionRef": "N202606081510252124",
            "data": data,
            "error": None,
        }

    def _complete_company_profile(self):
        self.company.company_name = "Prime Logistics"
        self.company.company_registration_number = "RC1754689"
        self.company.tax_identification_number = "1234567890"
        self.company.company_image = "companies/profile-images/existing.jpg"
        self.company.company_location_state = "Lagos"
        self.company.preferred_deployment_states = "Lagos, Abuja FCT"
        self.company.company_location_city = "Yaba"
        self.company.company_address = "10 Herbert Macaulay Way"
        self.company.company_sector = "Logistics"
        self.company.company_function = "Operations"
        self.company.ppa_capacity = 12
        self.company.office_location_count = 3
        self.company.desired_corper_description = "Need a corps member for company operations."
        self.company.desired_qualification = "B.Sc, HND"
        self.company.desired_age_range = "21-29"
        self.company.desired_field_of_study = "Business Administration, Accounting"
        self.company.desired_university = "University of Lagos, University of Ibadan"
        self.company.desired_posting_states = "Lagos, Abuja FCT"
        self.company.desired_skills = "Communication, Excel, coordination"
        self.company.desired_experience = "Internship or campus leadership"
        self.company.contact_name = "Grace Prime"
        self.company.contact_email = "grace@primelogistics.ng"
        self.company.contact_phone = "+2348030000000"
        self.company.terms_of_agreement_accepted_at = timezone.now()
        self.company.terms_of_use_accepted_at = timezone.now()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.PENDING
        self.company.save()

    def test_verification_endpoint_normalizes_registration_number_without_spaces(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/verification/",
            {
                "company_name": "Prime Logistics",
                "company_registration_number": "RC 1754689",
                "tax_identification_number": "1234567890",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_registration_number, "RC1754689")
        self.assertEqual(response.data["company_registration_number"], "RC1754689")

    def test_terms_submission_verifies_company_before_profile_completion(self):
        self.client.force_authenticate(self.company_user)
        self.client.patch(
            "/api/companies/me/verification/",
            {
                "company_name": "Prime Logistics",
                "company_registration_number": "RC1754689",
                "tax_identification_number": "1234567890",
            },
            format="json",
        )

        with patch(
            "apps.companies.views.verify_company_profile_or_raise", return_value={"companyName": "Prime Logistics"}
        ):
            response = self.client.post(
                "/api/companies/me/submit/",
                {
                    "accepted_terms_of_agreement": True,
                    "accepted_terms_of_use": True,
                    "accepted_documents": list(COMPANY_LEGAL_DOCUMENT_SLUGS),
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.verification_status, CompanyProfile.VerificationStatus.VERIFIED)
        self.assertTrue(self.company.terms_accepted)
        self.assertEqual(self.company.approval_status, CompanyProfile.ApprovalStatus.UNSUBMITTED)

    def test_admin_can_approve_completed_company_and_send_welcome_email(self):
        self._complete_company_profile()
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            f"/api/companies/admin/{self.company.id}/",
            {"approval_status": CompanyProfile.ApprovalStatus.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.approval_status, CompanyProfile.ApprovalStatus.APPROVED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to corpershub", mail.outbox[0].subject)

    @patch("apps.companies.verification.dikript_lookup")
    def test_company_verification_uses_only_cac_supported_fields(self, dikript_lookup_mock):
        self.company.company_name = "tconnect technologies ltd"
        self.company.company_registration_number = "RC9463122"
        self.company.company_registration_date = date(2026, 4, 4)
        self.company.tax_identification_number = "1234567890"
        self.company.company_location_state = "Lagos"
        self.company.company_location_city = "Yaba"
        dikript_lookup_mock.return_value = self._cac_payload(
            state="Kano",
            city="Kano",
        )

        returned_data = verify_company_profile_or_raise(self.company)

        self.assertEqual(returned_data["rcNumber"], "9463122")

    @patch("apps.companies.verification.dikript_lookup")
    def test_company_verification_rejects_registration_dates_outside_two_day_window(self, dikript_lookup_mock):
        self.company.company_name = "Tconnect Technologies Limited"
        self.company.company_registration_number = "RC9463122"
        self.company.company_registration_date = date(2026, 4, 6)
        self.company.tax_identification_number = "1234567890"
        dikript_lookup_mock.return_value = self._cac_payload()

        with self.assertRaises(ValidationError) as exc:
            verify_company_profile_or_raise(self.company)

        self.assertEqual(
            str(exc.exception.detail["company_registration_date"]),
            "The company registration date does not match the CAC record.",
        )

    def test_verified_company_edit_does_not_reverify_on_tax_id_or_state_change(self):
        self._complete_company_profile()
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/?edit=1",
            {
                "tax_identification_number": "9988776655",
                "company_location_state": "Ogun",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.tax_identification_number, "9988776655")
        self.assertEqual(self.company.company_location_state, "Ogun")
        self.assertEqual(self.company.verification_status, CompanyProfile.VerificationStatus.VERIFIED)
