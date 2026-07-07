import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.legal import COMPANY_LEGAL_DOCUMENT_SLUGS
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE
from apps.companies.services import ensure_company_profile
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class CompanyProfileAPITests(APITestCase):
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
        self.corper_user = User.objects.create_user(
            email="corper@corpershub.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.company = ensure_company_profile(self.company_user)

    def tearDown(self):
        self.override_media.disable()
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)
        super().tearDown()

    def complete_profile_payload(self):
        return {
            "company_name": "Prime Logistics",
            "company_registration_number": "RC 1029384",
            "tax_identification_number": "4433221100",
            "company_location_state": "Lagos",
            "preferred_deployment_states": "Lagos, Abuja FCT",
            "company_location_city": "Yaba",
            "company_address": "10 Herbert Macaulay Way",
            "head_office_address": "10 Herbert Macaulay Way",
            "company_website": "https://primelogistics.ng",
            "company_sector": "Logistics",
            "organization_type": "Private Company",
            "staff_count_range": "51-200",
            "ppa_capacity": "12",
            "office_location_count": "3",
            "company_function": "Operations",
            "placement_type": "Full-time / On-Site",
            "monthly_allowance_offered": "N25,000-N50,000",
            "accommodation_provided": "To be discussed",
            "ppa_support": "Yes",
            "desired_corper_description": "Need a corps member for company operations.",
            "desired_qualification": "B.Sc, HND",
            "desired_age_range": "21-29",
            "desired_field_of_study": "Business Administration, Accounting",
            "desired_university": "University of Lagos, University of Ibadan",
            "desired_posting_states": "Lagos, Abuja FCT",
            "desired_skills": "Communication, Excel, coordination",
            "desired_experience": "Internship or campus leadership",
            "contact_name": "Grace Prime",
            "contact_email": "grace@primelogistics.ng",
            "contact_phone": "+2348030000000",
            "directors_name": "Ada Prime",
            "director_phone_number": "+2348031111111",
        }

    def company_image_file(self):
        return SimpleUploadedFile(
            "company-image.jpg",
            b"fake-image-bytes",
            content_type="image/jpeg",
        )

    def make_company_profile_complete(self):
        self.company.company_name = "Prime Logistics"
        self.company.company_registration_number = "RC 1029384"
        self.company.tax_identification_number = "4433221100"
        self.company.company_image = "companies/profile-images/existing.jpg"
        self.company.company_location_state = "Lagos"
        self.company.preferred_deployment_states = "Lagos, Abuja FCT"
        self.company.company_location_city = "Yaba"
        self.company.company_address = "10 Herbert Macaulay Way"
        self.company.head_office_address = "10 Herbert Macaulay Way"
        self.company.company_website = "https://primelogistics.ng"
        self.company.company_sector = "Logistics"
        self.company.organization_type = "Private Company"
        self.company.staff_count_range = "51-200"
        self.company.ppa_capacity = 12
        self.company.office_location_count = 3
        self.company.company_function = "Operations"
        self.company.placement_type = "Full-time / On-Site"
        self.company.monthly_allowance_offered = "N25,000-N50,000"
        self.company.accommodation_provided = "To be discussed"
        self.company.ppa_support = "Yes"
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
        self.company.directors_name = "Ada Prime"
        self.company.director_phone_number = "+2348031111111"
        self.company.terms_of_agreement_accepted_at = timezone.now()
        self.company.terms_of_use_accepted_at = timezone.now()
        self.company.save()

    def activate_paid_corper_plan(self):
        plan = SubscriptionPlan.objects.get(code="six-months")
        starts_at = timezone.now()
        ends_at = calculate_subscription_end(plan=plan, starts_at=starts_at)
        UserSubscription.objects.create(
            user=self.corper_user,
            plan=plan,
            status=UserSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
            metadata={"source": "test"},
        )

    @patch("apps.companies.views.verify_company_profile_or_raise", return_value={"companyName": "Prime Logistics"})
    def test_complete_profile_moves_to_pending_review_on_submit(
        self,
        verify_company_mock,
    ):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()

        draft_response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(draft_response.status_code, 200)
        self.company.refresh_from_db()
        self.assertTrue(self.company.profile_fields_complete)
        self.assertFalse(self.company.is_complete)
        self.assertEqual(self.company.company_registration_number, "RC12345")
        self.assertEqual(
            self.company.verification_status,
            CompanyProfile.VerificationStatus.UNSUBMITTED,
        )

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
        self.assertTrue(self.company.is_complete)
        self.assertEqual(
            self.company.verification_status,
            CompanyProfile.VerificationStatus.VERIFIED,
        )
        self.assertEqual(
            self.company.approval_status,
            CompanyProfile.ApprovalStatus.APPROVED,
        )
        verify_company_mock.assert_called_once()

    def test_company_profile_requires_profile_photo(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/",
            self.complete_profile_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_image"][0],
            "Complete this field before saving your profile.",
        )

    def test_company_profile_requires_registration_and_tax_numbers(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload.pop("company_registration_number")
        payload.pop("tax_identification_number")

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            "Complete this field before saving your profile.",
        )
        self.assertEqual(
            response.data["tax_identification_number"][0],
            "Complete this field before saving your profile.",
        )

    def test_company_profile_rejects_invalid_registration_number_prefix(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["company_registration_number"] = "ABC 12345"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
        )

    def test_company_profile_rejects_invalid_registration_number_digit_length(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["company_registration_number"] = "RC 1234"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
        )

    def test_company_profile_accepts_hyphenated_registration_number(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["company_registration_number"] = "RC-12345"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_registration_number, "RC12345")
        self.assertEqual(response.data["company_registration_number"], "RC12345")

    def test_company_profile_rejects_non_international_contact_phone(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["contact_phone"] = "08030000000"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["contact_phone"][0],
            "Enter a valid Nigerian contact number starting with +234.",
        )

    def test_company_profile_rejects_non_numeric_tax_identification_number(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["tax_identification_number"] = "TIN4433221100"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["tax_identification_number"][0],
            "Enter a valid tax identification number with 10 to 13 digits.",
        )

    def test_company_profile_rejects_short_tax_identification_number(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["tax_identification_number"] = "123456789"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["tax_identification_number"][0],
            "Enter a valid tax identification number with 10 to 13 digits.",
        )

    def test_company_profile_rejects_long_tax_identification_number(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["tax_identification_number"] = "12345678901234"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["tax_identification_number"][0],
            "Enter a valid tax identification number with 10 to 13 digits.",
        )

    def test_company_can_upload_profile_image(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertTrue(bool(self.company.company_image))
        self.assertIn("/media/companies/profile-images/", response.data["company_image"])

    def test_directory_and_search_expose_company_image(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        update_response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(update_response.status_code, 200)
        self.company.refresh_from_db()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.APPROVED
        self.company.save(update_fields=["verification_status", "approval_status", "updated_at"])
        self.activate_paid_corper_plan()

        self.client.force_authenticate(self.corper_user)

        search_response = self.client.get("/api/search/companies/")
        detail_response = self.client.get(f"/api/companies/directory/{self.company.id}/")

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn("/media/companies/profile-images/", search_response.data["results"][0]["company_image"])
        self.assertIn("/media/companies/profile-images/", detail_response.data["company_image"])

    def test_verified_profile_rejects_locked_field_updates(self):
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.APPROVED
        self.company.save(update_fields=["verification_status", "approval_status", "updated_at"])
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/",
            {"company_name": "Updated Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Only the profile preferences and company image can be updated here. Contact admin/support team to change the remaining company fields.",
        )

    def test_verified_profile_allows_preference_updates(self):
        self.make_company_profile_complete()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.APPROVED
        self.company.desired_corper_description = "Current description"
        self.company.desired_qualification = "HND, B.Sc"
        self.company.desired_age_range = "21-27"
        self.company.desired_field_of_study = "Accounting, Economics"
        self.company.desired_university = "University of Lagos"
        self.company.desired_posting_states = "Lagos"
        self.company.desired_skills = "Communication"
        self.company.desired_experience = "Campus leadership"
        self.company.save(
            update_fields=[
                "company_name",
                "company_image",
                "company_location_state",
                "company_location_city",
                "company_address",
                "company_sector",
                "company_function",
                "verification_status",
                "approval_status",
                "desired_corper_description",
                "desired_qualification",
                "desired_age_range",
                "desired_field_of_study",
                "desired_university",
                "desired_posting_states",
                "desired_skills",
                "desired_experience",
                "contact_phone",
                "updated_at",
            ]
        )
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/",
            {
                "desired_corper_description": "Updated description",
                "desired_field_of_study": "Business Administration",
                "desired_university": "University of Ibadan",
                "desired_posting_states": "Abuja FCT",
                "desired_skills": "Communication, Excel",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.desired_corper_description, "Updated description")
        self.assertEqual(self.company.desired_field_of_study, "Business Administration")
        self.assertEqual(self.company.desired_university, "University of Ibadan")
        self.assertEqual(self.company.desired_posting_states, "Abuja FCT")
        self.assertEqual(self.company.desired_skills, "Communication, Excel")
        self.assertEqual(self.company.verification_status, CompanyProfile.VerificationStatus.VERIFIED)

    @patch("apps.companies.views.verify_company_profile_or_raise", return_value={"companyName": "Updated Name"})
    def test_verified_profile_edit_mode_resubmits_manual_review_when_ids_change(self, verify_company_mock):
        self.make_company_profile_complete()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.company_name = "Current Name"
        self.company.company_sector = "Technology"
        self.company.company_location_city = "Lagos"
        self.company.contact_phone = "+2348030000000"
        self.company.save(
            update_fields=[
                "company_name",
                "company_image",
                "company_location_state",
                "verification_status",
                "company_sector",
                "company_location_city",
                "company_address",
                "company_function",
                "desired_qualification",
                "desired_age_range",
                "desired_field_of_study",
                "desired_university",
                "desired_posting_states",
                "desired_skills",
                "desired_experience",
                "contact_phone",
                "updated_at",
            ]
        )
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/?edit=1",
            {
                "company_name": "Updated Name",
                "company_registration_number": "RC 5566778",
                "tax_identification_number": "9988776655",
                "company_sector": "Finance",
                "company_location_city": "Abuja",
                "contact_phone": "+2348035555555",
                "desired_corper_description": "Updated description",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Updated Name")
        self.assertEqual(self.company.company_registration_number, "RC5566778")
        self.assertEqual(self.company.tax_identification_number, "9988776655")
        self.assertEqual(self.company.company_sector, "Finance")
        self.assertEqual(self.company.company_location_city, "Abuja")
        self.assertEqual(self.company.contact_phone, "+2348035555555")
        self.assertEqual(self.company.desired_corper_description, "Updated description")
        self.assertEqual(self.company.verification_status, CompanyProfile.VerificationStatus.VERIFIED)
        self.assertEqual(self.company.approval_status, CompanyProfile.ApprovalStatus.APPROVED)
        verify_company_mock.assert_called_once()

    def test_verified_profile_edit_mode_allows_company_function_and_image_updates(self):
        self.make_company_profile_complete()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.company_function = "Operations"
        self.company.save(
            update_fields=[
                "company_name",
                "company_image",
                "company_location_state",
                "company_location_city",
                "company_address",
                "company_sector",
                "company_function",
                "desired_corper_description",
                "desired_qualification",
                "desired_age_range",
                "desired_field_of_study",
                "desired_university",
                "desired_posting_states",
                "desired_skills",
                "desired_experience",
                "contact_phone",
                "verification_status",
                "updated_at",
            ]
        )
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/companies/me/?edit=1",
            {
                "company_function": "Business Operations",
                "company_image": self.company_image_file(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_function, "Business Operations")
        self.assertTrue(bool(self.company.company_image))
        self.assertEqual(self.company.verification_status, CompanyProfile.VerificationStatus.VERIFIED)

    def test_company_profile_response_includes_registration_and_tax_numbers(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/companies/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("company_registration_number", response.data)
        self.assertIn("tax_identification_number", response.data)
        self.assertIn("head_office_address", response.data)
        self.assertIn("company_website", response.data)
        self.assertIn("organization_type", response.data)
        self.assertIn("staff_count_range", response.data)
        self.assertIn("placement_type", response.data)
        self.assertIn("monthly_allowance_offered", response.data)
        self.assertIn("accommodation_provided", response.data)
        self.assertIn("ppa_support", response.data)
        self.assertIn("preferred_deployment_states", response.data)
        self.assertIn("desired_university", response.data)
        self.assertIn("desired_posting_states", response.data)
        self.assertIn("contact_name", response.data)
        self.assertIn("contact_email", response.data)
        self.assertIn("directors_name", response.data)
        self.assertIn("director_phone_number", response.data)

    def test_company_profile_persists_optional_business_details(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["company_location_state"] = "Lagos, Ogun"
        payload["preferred_deployment_states"] = "Lagos, Ogun, Oyo"
        payload["desired_university"] = "University of Lagos"
        payload["desired_posting_states"] = "Ogun, Oyo"
        payload["head_office_address"] = "17 Marina Road"
        payload["company_website"] = "https://careers.primelogistics.ng"
        payload["organization_type"] = "Education Technology Startup"
        payload["staff_count_range"] = "Above 1000"
        payload["placement_type"] = "Part-Time / Hybrid, Full-time / Remote"
        payload["monthly_allowance_offered"] = "Negotiable"
        payload["accommodation_provided"] = "No"
        payload["ppa_support"] = "Willing to discuss"
        payload["contact_name"] = "Tunde Prime"
        payload["contact_email"] = "tunde@primelogistics.ng"
        payload["directors_name"] = "Tunde Prime"
        payload["director_phone_number"] = "+2348032222222"

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_location_state, "Lagos, Ogun")
        self.assertEqual(self.company.preferred_deployment_states, "Lagos, Ogun, Oyo")
        self.assertEqual(self.company.desired_university, "University of Lagos")
        self.assertEqual(self.company.desired_posting_states, "Ogun, Oyo")
        self.assertEqual(self.company.head_office_address, "17 Marina Road")
        self.assertEqual(self.company.company_website, "https://careers.primelogistics.ng")
        self.assertEqual(self.company.organization_type, "Education Technology Startup")
        self.assertEqual(self.company.staff_count_range, "Above 1000")
        self.assertEqual(self.company.placement_type, "Part-Time / Hybrid, Full-time / Remote")
        self.assertEqual(self.company.monthly_allowance_offered, "Negotiable")
        self.assertEqual(self.company.accommodation_provided, "No")
        self.assertEqual(self.company.ppa_support, "Willing to discuss")
        self.assertEqual(self.company.contact_name, "Tunde Prime")
        self.assertEqual(self.company.contact_email, "tunde@primelogistics.ng")
        self.assertEqual(self.company.directors_name, "Tunde Prime")
        self.assertEqual(self.company.director_phone_number, "+2348032222222")

    def test_company_profile_allows_optional_company_fields_to_be_blank(self):
        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()
        payload["company_registration_date"] = ""
        payload["company_website"] = ""
        payload["office_location_count"] = ""
        payload["company_function"] = ""
        payload["monthly_allowance_offered"] = ""

        response = self.client.patch(
            "/api/companies/me/",
            payload,
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertIsNone(self.company.company_registration_date)
        self.assertEqual(self.company.company_website, "")
        self.assertIsNone(self.company.office_location_count)
        self.assertEqual(self.company.company_function, "")
        self.assertEqual(self.company.monthly_allowance_offered, "")
        self.assertTrue(self.company.profile_fields_complete)

    def test_company_profile_rejects_duplicate_name(self):
        other_user = User.objects.create_user(
            email="second-company@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        other_company = ensure_company_profile(other_user)
        other_company.company_name = "Prime Logistics"
        other_company.company_registration_number = "RC 2093847"
        other_company.save(update_fields=["company_name", "company_registration_number", "updated_at"])

        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()

        response = self.client.patch("/api/companies/me/", payload, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["company_name"][0], "A company with this name already exists.")

    def test_company_profile_rejects_duplicate_registration_number(self):
        other_user = User.objects.create_user(
            email="third-company@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        other_company = ensure_company_profile(other_user)
        other_company.company_name = "Second Prime Logistics"
        other_company.company_registration_number = "RC 1029384"
        other_company.save(update_fields=["company_name", "company_registration_number", "updated_at"])

        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()

        response = self.client.patch("/api/companies/me/", payload, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            "A company with this registration number already exists.",
        )

    def test_company_profile_rejects_duplicate_tax_identification_number(self):
        other_user = User.objects.create_user(
            email="fourth-company@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        other_company = ensure_company_profile(other_user)
        other_company.company_name = "Third Prime Logistics"
        other_company.company_registration_number = "RC 9081726"
        other_company.tax_identification_number = "4433221100"
        other_company.save(
            update_fields=[
                "company_name",
                "company_registration_number",
                "tax_identification_number",
                "updated_at",
            ]
        )

        self.client.force_authenticate(self.company_user)
        payload = self.complete_profile_payload()
        payload["company_image"] = self.company_image_file()

        response = self.client.patch("/api/companies/me/", payload, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertIn("tax identification number", str(response.data["tax_identification_number"][0]).lower())
        self.assertIn("already exists", str(response.data["tax_identification_number"][0]).lower())

    def test_admin_can_verify_company_profile(self):
        self.make_company_profile_complete()
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.PENDING
        self.company.save(update_fields=["verification_status", "approval_status", "updated_at"])
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            f"/api/companies/admin/{self.company.id}/",
            {"approval_status": CompanyProfile.ApprovalStatus.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(
            self.company.approval_status,
            CompanyProfile.ApprovalStatus.APPROVED,
        )

    def test_admin_can_reject_company_profile(self):
        self.company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        self.company.approval_status = CompanyProfile.ApprovalStatus.PENDING
        self.company.save(update_fields=["verification_status", "approval_status", "updated_at"])
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            f"/api/companies/admin/{self.company.id}/",
            {"approval_status": CompanyProfile.ApprovalStatus.REJECTED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company.refresh_from_db()
        self.assertEqual(
            self.company.approval_status,
            CompanyProfile.ApprovalStatus.REJECTED,
        )
