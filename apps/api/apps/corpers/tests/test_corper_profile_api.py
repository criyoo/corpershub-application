import shutil
import tempfile
import json
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.verification.models import VerificationAttempt


class CorperProfileAPITests(APITestCase):
    def setUp(self):
        self.temp_media_dir = tempfile.mkdtemp()
        self.override_media = override_settings(MEDIA_ROOT=self.temp_media_dir)
        self.override_media.enable()
        self.corper_user = User.objects.create_user(
            email="corper@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.client.force_authenticate(self.corper_user)

    def tearDown(self):
        self.override_media.disable()
        shutil.rmtree(self.temp_media_dir, ignore_errors=True)
        super().tearDown()

    def biodata_submission_payload(self, **overrides):
        payload = {
            "verification_type": VerificationAttempt.VerificationType.BIODATA,
            "full_name": "Ada Lovelace",
            "date_of_birth": "2001-06-15",
            "gender": "female",
            "mobile_number": "08099446062",
        }
        payload.update(overrides)
        return payload

    class _FakeHTTPResponse:
        def __init__(self, payload: dict):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def test_blank_profile_starts_with_empty_graduation_year(self):
        response = self.client.get("/api/corpers/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "corper@example.com")
        self.assertIsNone(response.data["graduation_year"])
        self.assertFalse(response.data["is_complete"])

    def test_profile_update_requires_completed_verification(self):
        response = self.client.patch(
            "/api/corpers/me/",
            {"gender": "female"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Complete biodata, NIN, NYSC call-up, and NYSC state code verification before editing your profile.",
        )

    def test_profile_update_requires_all_fields_before_save(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/199"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "32345678901"
        corper.nysc_callup_number = "NYSC/BEN/2026/199999"
        corper.nysc_state_code = "NYSC/BE/26A/0997"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.posting_location_state = "Lagos"
        corper.batch = "Batch A"
        corper.stream = "Stream 1"
        corper.field_of_study = "Computer Science"
        corper.degree = "BSc"
        corper.university = "University of Lagos"
        corper.graduation_year = 2026
        corper.technical_skills = "Product Design"
        corper.soft_skills = "Communication"
        corper.languages_spoken = "English"
        corper.available_date = "2027-03-01"
        corper.bio = "Ready for NYSC placement."
        corper.terms_of_agreement_accepted_at = timezone.now()
        corper.terms_of_use_accepted_at = timezone.now()
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "posting_location_state",
                "batch",
                "stream",
                "field_of_study",
                "degree",
                "university",
                "graduation_year",
                "technical_skills",
                "soft_skills",
                "languages_spoken",
                "available_date",
                "bio",
                "terms_of_agreement_accepted_at",
                "terms_of_use_accepted_at",
                "updated_at",
            ]
        )

        response = self.client.patch(
            "/api/corpers/me/",
            {"gender": "female"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["profile_photo"][0],
            "Complete this field before saving your profile.",
        )
        self.assertEqual(
            response.data["mobile_number"][0],
            "Complete this field before saving your profile.",
        )

    def test_updating_complete_profile_keeps_verified_status_without_profile_review_attempt(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/299"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "42345678901"
        corper.nysc_callup_number = "NYSC/BEN/2026/299999"
        corper.nysc_state_code = "NYSC/BE/26A/0996"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )
        photo = SimpleUploadedFile("profile-photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.patch(
            "/api/corpers/me/",
            {
                "posting_location_state": "Lagos",
                "batch": "Batch A",
                "stream": "Stream 1",
                "field_of_study": "Computer Science",
                "degree": "BSc",
                "university": "University of Lagos",
                "graduation_year": "2026",
                "profile_photo": photo,
                "mobile_number": "+2348031234567",
                "technical_skills": "Product Design",
                "soft_skills": "Communication",
                "languages_spoken": "English",
                "available_date": "2027-03-01",
                "bio": "Ready for NYSC placement.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Accept every required legal document before editing your corper profile.",
        )

    def test_verified_profile_rejects_locked_field_updates(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Verified Corper"
        corper.date_of_birth = "2000-01-01"
        corper.posting_location_state = "Lagos"
        corper.batch = "Batch B"
        corper.stream = "Stream 1"
        corper.university_matriculation_number = "UNILAG/ENG/001"
        corper.field_of_study = "Engineering"
        corper.degree = "BEng"
        corper.university = "UNILAG"
        corper.graduation_year = 2026
        corper.mobile_number = "08031234567"
        corper.nysc_callup_number = "NYSC/BEN/2026/111111"
        corper.nysc_state_code = "NYSC/BE/26A/0456"
        corper.nin_number = "12345678901"
        corper.skill = "Operations"
        corper.bio = "Existing bio."
        corper.profile_photo = "corpers/profile-photos/existing.jpg"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.technical_skills = "Operations"
        corper.soft_skills = "Communication"
        corper.languages_spoken = "English"
        corper.available_date = "2026-01-01"
        corper.terms_of_agreement_accepted_at = timezone.now()
        corper.terms_of_use_accepted_at = timezone.now()
        corper.verification_status = CorperProfile.VerificationStatus.VERIFIED
        corper.save()

        response = self.client.patch(
            "/api/corpers/me/",
            {"full_name": "Changed Name"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Use the verification center to submit your verified identity details, NIN, NYSC call-up number, and NYSC state code.",
        )

    def test_verified_profile_allows_posting_state_skill_and_bio_updates(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Verified Corper"
        corper.date_of_birth = "2000-01-01"
        corper.posting_location_state = "Lagos"
        corper.batch = "Batch B"
        corper.stream = "Stream 1"
        corper.university_matriculation_number = "UNILAG/ENG/001"
        corper.field_of_study = "Engineering"
        corper.degree = "BEng"
        corper.university = "UNILAG"
        corper.graduation_year = 2026
        corper.mobile_number = "08031234567"
        corper.nysc_callup_number = "NYSC/BEN/2026/111111"
        corper.nysc_state_code = "NYSC/BE/26A/0456"
        corper.nin_number = "12345678901"
        corper.skill = "Operations"
        corper.bio = "Existing bio."
        corper.profile_photo = "corpers/profile-photos/existing.jpg"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.technical_skills = "Operations"
        corper.soft_skills = "Communication"
        corper.languages_spoken = "English"
        corper.available_date = "2026-01-01"
        corper.terms_of_agreement_accepted_at = timezone.now()
        corper.terms_of_use_accepted_at = timezone.now()
        corper.verification_status = CorperProfile.VerificationStatus.VERIFIED
        corper.save()

        response = self.client.patch(
            "/api/corpers/me/",
            {
                "gender": "female",
                "posting_location_state": "Abuja FCT",
                "technical_skills": "Project Management",
                "soft_skills": "Communication",
                "languages_spoken": "English",
                "bio": "Updated bio.",
                "preferred_sector": "Technology & IT",
                "preferred_organization_type": "Private Company",
                "preferred_placement_type": "Full-time / Hybrid",
                "preferred_monthly_allowance": "N50,000-N100,000",
                "preferred_organization_experience": "I have worked on internal tools.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        corper.refresh_from_db()
        self.assertEqual(corper.gender, "female")
        self.assertEqual(corper.posting_location_state, "Abuja FCT")
        self.assertEqual(corper.skill, "Project Management | Communication")
        self.assertEqual(corper.technical_skills, "Project Management")
        self.assertEqual(corper.soft_skills, "Communication")
        self.assertEqual(corper.bio, "Updated bio.")
        self.assertEqual(corper.preferred_sector, "Technology & IT")
        self.assertEqual(corper.preferred_organization_type, "Private Company")
        self.assertEqual(corper.preferred_placement_type, "Full-time / Hybrid")
        self.assertEqual(corper.preferred_monthly_allowance, "N50,000-N100,000")
        self.assertEqual(corper.preferred_organization_experience, "I have worked on internal tools.")
        self.assertEqual(corper.verification_status, CorperProfile.VerificationStatus.VERIFIED)
        self.assertEqual(
            VerificationAttempt.objects.filter(
                corper=corper,
                verification_type=VerificationAttempt.VerificationType.PROFILE,
            ).count(),
            0,
        )

    def test_profile_response_exposes_verified_document_values(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/001"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "12345678901"
        corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        corper.nysc_state_code = "NYSC/BE/27A/0123"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.terms_of_agreement_accepted_at = timezone.now()
        corper.terms_of_use_accepted_at = timezone.now()
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "terms_of_agreement_accepted_at",
                "terms_of_use_accepted_at",
                "updated_at",
            ]
        )

        response = self.client.get("/api/corpers/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nin_number"], "12345678901")
        self.assertEqual(response.data["nysc_callup_number"], "NYSC/BEN/2027/123456")
        self.assertEqual(response.data["nysc_state_code"], "NYSC/BE/27A/0123")

    def test_biodata_verification_submission_stays_pending_until_review(self):
        response = self.client.post(
            "/api/verification/attempts/",
            self.biodata_submission_payload(
                university_matriculation_number="UNILAG/CSC/001",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.PENDING)
        self.assertEqual(attempt.metadata["full_name"], "Ada Lovelace")
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.biodata_verification_status, CorperProfile.SensitiveStatus.PENDING)
        self.assertEqual(corper.full_name, "Ada Lovelace")
        self.assertEqual(str(corper.date_of_birth), "2001-06-15")
        self.assertEqual(corper.gender, "female")
        self.assertEqual(corper.mobile_number, "+2348097654321")
        self.assertEqual(corper.university_matriculation_number, "UNILAG/CSC/001")

    def test_biodata_verification_submission_rejects_invalid_matriculation_number(self):
        response = self.client.post(
            "/api/verification/attempts/",
            self.biodata_submission_payload(
                university_matriculation_number="LASU-2017-09876",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["university_matriculation_number"][0],
            'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".',
        )
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            attempt.review_note,
            'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".',
        )
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.biodata_verification_status, CorperProfile.SensitiveStatus.UNSUBMITTED)
        self.assertEqual(corper.university_matriculation_number, "")

    def test_biodata_verification_submission_rejects_duplicate_matriculation_number(self):
        other_user = User.objects.create_user(
            email="second.corper@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        other_corper = ensure_corper_profile(other_user)
        other_corper.university_matriculation_number = "unilag/csc/001"
        other_corper.save(update_fields=["university_matriculation_number", "updated_at"])

        response = self.client.post(
            "/api/verification/attempts/",
            self.biodata_submission_payload(
                university_matriculation_number="UNILAG/CSC/001",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "This university matriculation number has already been submitted.",
        )

    def test_biodata_verification_submission_rejects_duplicate_mobile_number(self):
        other_user = User.objects.create_user(
            email="mobile.duplicate@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        other_corper = ensure_corper_profile(other_user)
        other_corper.mobile_number = "+2348099446333"
        other_corper.save(update_fields=["mobile_number", "updated_at"])

        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Ada",
                "surname": "Lovelace",
                "date_of_birth": "2001-06-15",
                "gender": "female",
                "mobile_number": "08099446333",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "This mobile number has already been submitted.",
        )

    def test_verification_submission_humanizes_integrity_errors(self):
        ensure_corper_profile(self.corper_user)

        with patch(
            "apps.verification.views.CorperProfile.save",
            side_effect=IntegrityError(
                "duplicate key value violates unique constraint "
                '"corpers_unique_mobile_number" DETAIL: Key (mobile_number)=(+2348099446062) already exists.'
            ),
        ):
            response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.BIODATA,
                    "first_name": "Ada",
                    "surname": "Lovelace",
                    "date_of_birth": "2001-06-15",
                    "gender": "female",
                    "mobile_number": "08099446062",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "This mobile number has already been submitted.",
        )
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            attempt.review_note,
            "This mobile number has already been submitted.",
        )

    def test_verification_submission_humanizes_duplicate_errors_from_generic_exceptions(self):
        ensure_corper_profile(self.corper_user)

        with patch(
            "apps.verification.views.CorperProfile.save",
            side_effect=RuntimeError("DETAIL: Key (mobile_number)=(+2348099446062) already exists."),
        ):
            response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.BIODATA,
                    "first_name": "Ada",
                    "surname": "Lovelace",
                    "date_of_birth": "2001-06-15",
                    "gender": "female",
                    "mobile_number": "08099446062",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "This mobile number has already been submitted.",
        )
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            attempt.review_note,
            "This mobile number has already been submitted.",
        )

    @patch(
        "apps.verification.views.dikript_lookup",
        return_value={
            "status": True,
            "message": "Successful",
            "transactionRef": "test-ref",
            "data": {
                "firstName": "ADA",
                "surname": "LOVELACE",
                "middleName": "",
                "birthDate": "2001-06-15",
                "gender": "Female",
                "nin": "12345678901",
                "vNin": "12345678901",
                "telephoneNo": "08099446062",
                "birthCountry": "",
                "selfOriginState": "",
            },
        },
    )
    def test_verification_submission_stores_sensitive_corper_values(self, dikript_lookup_mock):
        callup_document = SimpleUploadedFile(
            "callup-letter.pdf",
            b"%PDF-1.4 fake callup",
            content_type="application/pdf",
        )
        state_code_document = SimpleUploadedFile(
            "state-code-card.pdf",
            b"%PDF-1.4 fake state code",
            content_type="application/pdf",
        )
        biodata_response = self.client.post(
            "/api/verification/attempts/",
            self.biodata_submission_payload(
                first_name="Ada",
                surname="Lovelace",
                full_name="Ada Lovelace",
                university_matriculation_number="UNILAG/CSC/599",
            ),
            format="json",
        )
        nin_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.NIN,
                "submitted_value": "12345678901",
            },
            format="json",
        )
        callup_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "nysc/ben/2027/123456",
                "document": callup_document,
            },
            format="multipart",
        )
        state_code_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "nysc/be/27a/0123",
                "document": state_code_document,
            },
            format="multipart",
        )

        self.assertEqual(biodata_response.status_code, 201)
        self.assertEqual(nin_response.status_code, 201)
        self.assertEqual(callup_response.status_code, 201)
        self.assertEqual(state_code_response.status_code, 201)

        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.nin_last4, "8901")
        self.assertEqual(corper.masked_callup_number, "NY****************56")
        self.assertEqual(corper.masked_state_code, "NYSC**********23")
        self.assertEqual(corper.nin_verification_status, CorperProfile.SensitiveStatus.VERIFIED)
        self.assertEqual(corper.nysc_callup_verification_status, CorperProfile.SensitiveStatus.VERIFIED)
        self.assertEqual(corper.nysc_state_code_verification_status, CorperProfile.SensitiveStatus.VERIFIED)
        self.assertEqual(corper.nin_number, "12345678901")
        self.assertEqual(corper.nysc_callup_number, "NYSC/BEN/2027/123456")
        self.assertEqual(corper.nysc_state_code, "NYSC/BE/27A/0123")
        dikript_lookup_mock.assert_called_once()

    def test_callup_and_state_code_submission_require_uploaded_documents(self):
        callup_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "NYSC/BEN/2027/123456",
            },
            format="json",
        )
        state_code_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "NYSC/BE/27A/0123",
            },
            format="json",
        )

        self.assertEqual(callup_response.status_code, 400)
        self.assertEqual(callup_response.data["document"][0], "Upload the NYSC document.")
        self.assertEqual(state_code_response.status_code, 400)
        self.assertEqual(state_code_response.data["document"][0], "Upload the NYSC document.")

    def test_nysc_document_submission_stores_uploaded_files_and_attempt_metadata(self):
        callup_document = SimpleUploadedFile(
            "callup-letter.pdf",
            b"%PDF-1.4 fake callup",
            content_type="application/pdf",
        )
        state_code_document = SimpleUploadedFile(
            "state-code-card.pdf",
            b"%PDF-1.4 fake state code",
            content_type="application/pdf",
        )

        callup_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "NYSC/BEN/2027/123456",
                "document": callup_document,
            },
            format="multipart",
        )
        state_code_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "NYSC/BE/27A/0123",
                "document": state_code_document,
            },
            format="multipart",
        )

        self.assertEqual(callup_response.status_code, 201)
        self.assertEqual(state_code_response.status_code, 201)

        corper = ensure_corper_profile(self.corper_user)
        self.assertTrue(corper.nysc_callup_document.name.endswith(".pdf"))
        self.assertTrue(corper.nysc_state_code_document.name.endswith(".pdf"))

        callup_attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
        )
        state_code_attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.STATE_CODE,
        )
        self.assertTrue(callup_attempt.metadata["document_name"].endswith(".pdf"))
        self.assertIn("/media/corpers/verification-documents/callup/", callup_attempt.metadata["document_path"])
        self.assertTrue(state_code_attempt.metadata["document_name"].endswith(".pdf"))
        self.assertIn(
            "/media/corpers/verification-documents/state-code/",
            state_code_attempt.metadata["document_path"],
        )

        profile_response = self.client.get("/api/corpers/me/")

        self.assertEqual(profile_response.status_code, 200)
        self.assertIn("/media/corpers/verification-documents/callup/", profile_response.data["nysc_callup_document"])
        self.assertIn(
            "/media/corpers/verification-documents/state-code/",
            profile_response.data["nysc_state_code_document"],
        )

    def test_verification_submission_rejects_invalid_nin_number(self):
        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.NIN,
                "submitted_value": "12345",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["submitted_value"][0], "NIN Number must be exactly 11 digits.")
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.NIN,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(attempt.review_note, "NIN Number must be exactly 11 digits.")
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.nin_verification_status, CorperProfile.SensitiveStatus.UNSUBMITTED)
        self.assertEqual(corper.nin_number, "")

    def test_verification_submission_rejects_invalid_callup_number(self):
        callup_document = SimpleUploadedFile(
            "callup-letter.pdf",
            b"%PDF-1.4 fake callup",
            content_type="application/pdf",
        )
        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "BEN/2027/123456",
                "document": callup_document,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["submitted_value"][0],
            "NYSC Call-up Number must match the format NYSC/ABC/2024/1234.",
        )
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            attempt.review_note,
            "NYSC Call-up Number must match the format NYSC/ABC/2024/1234.",
        )

    def test_verification_submission_rejects_invalid_state_code(self):
        state_code_document = SimpleUploadedFile(
            "state-code-card.pdf",
            b"%PDF-1.4 fake state code",
            content_type="application/pdf",
        )
        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "NYSC/LAG/2027/1234",
                "document": state_code_document,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["submitted_value"][0],
            "NYSC State Code must match the format NYSC/AB/23A/0123.",
        )
        attempt = VerificationAttempt.objects.get(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.STATE_CODE,
        )
        self.assertEqual(attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            attempt.review_note,
            "NYSC State Code must match the format NYSC/AB/23A/0123.",
        )

    def test_verification_submission_records_failed_attempt_when_profile_update_fails(self):
        ensure_corper_profile(self.corper_user)

        with patch("apps.verification.views.CorperProfile.save", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.BIODATA,
                    "first_name": "Ada",
                    "surname": "Lovelace",
                    "date_of_birth": "2001-06-15",
                    "gender": "female",
                    "mobile_number": "08099446062",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data["detail"],
            "Unable to submit verification right now. Please try again.",
        )
        attempts = VerificationAttempt.objects.filter(
            corper__user=self.corper_user,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
        ).order_by("created_at")
        self.assertEqual(attempts.count(), 1)
        self.assertEqual(attempts.first().status, VerificationAttempt.Status.FAILED)
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.biodata_verification_status, CorperProfile.SensitiveStatus.UNSUBMITTED)
        self.assertEqual(corper.mobile_number, "")

    @override_settings(
        DIKRIPT_API_BASE_URL="https://api.dikript.com",
        DIKRIPT_NIN_API_URL="/dikript/verification/api/v1/getnin",
        DIKRIPT_SECRET_KEY="test-key",
        DIKRIPT_TIMEOUT_SECONDS=10,
    )
    def test_nin_verification_accepts_live_payload_shape_with_blank_optional_fields(self):
        cache.clear()
        biodata_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "middle_name": "Odezi",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "08099446062",
                "state_of_origin": "Delta",
                "country_of_birth": "Nigeria",
            },
            format="json",
        )
        self.assertEqual(biodata_response.status_code, 201)

        live_payload = {
            "status": True,
            "message": "Successful",
            "code": "200",
            "apiVersion": "v1",
            "transactionRef": "N202606040234438506",
            "data": {
                "firstName": "CHRISTIAN",
                "birthDate": "1977-02-06",
                "gender": "Male",
                "middleName": "ODEZI",
                "nin": "91231161558",
                "vNin": "91231161558",
                "birthCountry": "",
                "selfOriginState": "",
                "surname": "ALUYA",
                "telephoneNo": "08099446062",
                "title": "Mr",
                "trackingId": "",
            },
            "error": None,
        }

        with patch(
            "apps.verification.dikript.urlopen",
            return_value=self._FakeHTTPResponse(live_payload),
        ):
            nin_response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.NIN,
                    "submitted_value": "91231161558",
                },
                format="json",
            )

        self.assertEqual(nin_response.status_code, 201)
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.nin_number, "91231161558")
        self.assertEqual(corper.nin_verification_status, CorperProfile.SensitiveStatus.VERIFIED)

    @override_settings(
        DIKRIPT_API_BASE_URL="https://api.dikript.com",
        DIKRIPT_NIN_API_URL="/dikript/verification/api/v1/getnin",
        DIKRIPT_SECRET_KEY="test-key",
        DIKRIPT_TIMEOUT_SECONDS=10,
    )
    def test_nin_verification_accepts_gender_and_birth_date_format_variants(self):
        cache.clear()
        biodata_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "middle_name": "Odezi",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "08099446062",
                "state_of_origin": "Delta",
                "country_of_birth": "Nigeria",
            },
            format="json",
        )
        self.assertEqual(biodata_response.status_code, 201)

        live_payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "firstName": "CHRISTIAN",
                "birthDate": "06/02/1977",
                "gender": "M",
                "middleName": "ODEZI",
                "nin": "91231161558",
                "vNin": "91231161558",
                "birthCountry": "",
                "selfOriginState": "",
                "surname": "ALUYA",
                "telephoneNo": "08099446062",
            },
        }

        with patch(
            "apps.verification.dikript.urlopen",
            return_value=self._FakeHTTPResponse(live_payload),
        ):
            nin_response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.NIN,
                    "submitted_value": "91231161558",
                },
                format="json",
            )

        self.assertEqual(nin_response.status_code, 201)
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.nin_number, "91231161558")
        self.assertEqual(corper.nin_verification_status, CorperProfile.SensitiveStatus.VERIFIED)

    @override_settings(
        DIKRIPT_API_BASE_URL="https://api.dikript.com",
        DIKRIPT_NIN_API_URL="/dikript/verification/api/v1/getnin",
        DIKRIPT_SECRET_KEY="test-key",
        DIKRIPT_TIMEOUT_SECONDS=10,
    )
    def test_nin_verification_accepts_numeric_nin_and_optional_blank_middle_name(self):
        cache.clear()
        biodata_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.BIODATA,
                "first_name": "Christian",
                "middle_name": "Odezi",
                "surname": "Aluya",
                "date_of_birth": "1977-02-06",
                "gender": "male",
                "mobile_number": "08099446062",
                "state_of_origin": "Delta",
                "country_of_birth": "Nigeria",
            },
            format="json",
        )
        self.assertEqual(biodata_response.status_code, 201)

        live_payload = {
            "status": True,
            "message": "Successful",
            "data": {
                "firstName": "CHRISTIAN",
                "birthDate": "1977/02/06",
                "gender": "m",
                "middleName": "",
                "nin": 91231161558,
                "surname": "ALUYA",
                "telephoneNo": "08099446062",
            },
        }

        with patch(
            "apps.verification.dikript.urlopen",
            return_value=self._FakeHTTPResponse(live_payload),
        ):
            nin_response = self.client.post(
                "/api/verification/attempts/",
                {
                    "verification_type": VerificationAttempt.VerificationType.NIN,
                    "submitted_value": "91231161558",
                },
                format="json",
            )

        self.assertEqual(nin_response.status_code, 201)
        corper = ensure_corper_profile(self.corper_user)
        self.assertEqual(corper.nin_number, "91231161558")
        self.assertEqual(corper.nin_verification_status, CorperProfile.SensitiveStatus.VERIFIED)

    def test_profile_update_rejects_invalid_mobile_number(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/001"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "12345678901"
        corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        corper.nysc_state_code = "NYSC/BE/27A/0123"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )
        photo = SimpleUploadedFile("profile-photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.patch(
            "/api/corpers/me/",
            {
                "posting_location_state": "Lagos",
                "batch": "Batch A",
                "stream": "Stream 1",
                "field_of_study": "Computer Science",
                "degree": "BSc",
                "university": "University of Lagos",
                "graduation_year": "2026",
                "profile_photo": photo,
                "mobile_number": "+2340000000000",
                "skill": "Product Design",
                "bio": "Ready for NYSC placement.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Accept every required legal document before editing your corper profile.",
        )

    def test_profile_update_requires_corper_mobile_number_in_plus_234_format(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/001"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "12345678901"
        corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        corper.nysc_state_code = "NYSC/BE/27A/0123"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )
        photo = SimpleUploadedFile("profile-photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.patch(
            "/api/corpers/me/",
            {
                "posting_location_state": "Lagos",
                "batch": "Batch A",
                "stream": "Stream 1",
                "field_of_study": "Computer Science",
                "degree": "BSc",
                "university": "University of Lagos",
                "graduation_year": "2027",
                "profile_photo": photo,
                "mobile_number": "08031234567",
                "skill": "Product Design",
                "bio": "Ready for NYSC placement.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Accept every required legal document before editing your corper profile.",
        )

    def test_verified_documents_cannot_be_resubmitted(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.nin_number = "12345678901"
        corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        corper.nysc_state_code = "NYSC/BE/27A/0123"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "nin_number",
                "nin_last4",
                "nysc_callup_number",
                "nysc_state_code",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )

        nin_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.NIN,
                "submitted_value": "10987654321",
            },
            format="json",
        )
        callup_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "NYSC/ABJ/2028/654321",
                "document": SimpleUploadedFile(
                    "callup-letter.pdf",
                    b"%PDF-1.4 fake callup",
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )
        state_code_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "NYSC/AB/28A/0456",
                "document": SimpleUploadedFile(
                    "state-code-card.pdf",
                    b"%PDF-1.4 fake state code",
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )

        self.assertEqual(nin_response.status_code, 400)
        self.assertEqual(nin_response.data["detail"], "Your NIN has already been verified.")
        self.assertEqual(callup_response.status_code, 400)
        self.assertEqual(
            callup_response.data["detail"],
            "Your NYSC call-up number has already been verified.",
        )
        self.assertEqual(state_code_response.status_code, 400)
        self.assertEqual(
            state_code_response.data["detail"],
            "Your NYSC state code has already been verified.",
        )
        nin_attempt = VerificationAttempt.objects.get(
            corper=corper,
            verification_type=VerificationAttempt.VerificationType.NIN,
        )
        self.assertEqual(nin_attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(nin_attempt.review_note, "Your NIN has already been verified.")
        callup_attempt = VerificationAttempt.objects.get(
            corper=corper,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
        )
        self.assertEqual(callup_attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            callup_attempt.review_note,
            "Your NYSC call-up number has already been verified.",
        )
        state_code_attempt = VerificationAttempt.objects.get(
            corper=corper,
            verification_type=VerificationAttempt.VerificationType.STATE_CODE,
        )
        self.assertEqual(state_code_attempt.status, VerificationAttempt.Status.FAILED)
        self.assertEqual(
            state_code_attempt.review_note,
            "Your NYSC state code has already been verified.",
        )

    def test_duplicate_sensitive_identifiers_are_rejected_across_corpers(self):
        other_user = User.objects.create_user(
            email="another.corper@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        other_corper = ensure_corper_profile(other_user)
        other_corper.nin_number = "12345678901"
        other_corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        other_corper.nysc_state_code = "NYSC/BE/27A/0123"
        other_corper.save(
            update_fields=[
                "nin_number",
                "nin_last4",
                "nin_lookup_hash",
                "nysc_callup_number",
                "nysc_callup_lookup_hash",
                "nysc_state_code",
                "nysc_state_code_lookup_hash",
                "updated_at",
            ]
        )

        biodata_response = self.client.post(
            "/api/verification/attempts/",
            self.biodata_submission_payload(),
            format="json",
        )
        self.assertEqual(biodata_response.status_code, 201)

        nin_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.NIN,
                "submitted_value": "12345678901",
            },
            format="json",
        )
        callup_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.CALLUP,
                "submitted_value": "NYSC/BEN/2027/123456",
                "document": SimpleUploadedFile(
                    "callup-letter.pdf",
                    b"%PDF-1.4 fake callup",
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )
        state_code_response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": VerificationAttempt.VerificationType.STATE_CODE,
                "submitted_value": "NYSC/BE/27A/0123",
                "document": SimpleUploadedFile(
                    "state-code-card.pdf",
                    b"%PDF-1.4 fake state code",
                    content_type="application/pdf",
                ),
            },
            format="multipart",
        )

        self.assertEqual(nin_response.status_code, 400)
        self.assertEqual(nin_response.data["detail"], "This NIN number has already been submitted.")
        self.assertEqual(callup_response.status_code, 400)
        self.assertEqual(
            callup_response.data["detail"],
            "This NYSC call-up number has already been submitted.",
        )
        self.assertEqual(state_code_response.status_code, 400)
        self.assertEqual(
            state_code_response.data["detail"],
            "This NYSC state code has already been submitted.",
        )
        self.assertEqual(
            VerificationAttempt.objects.filter(
                corper__user=self.corper_user,
                status=VerificationAttempt.Status.FAILED,
            ).count(),
            3,
        )

    def test_profile_update_rejects_duplicate_mobile_number(self):
        other_user = User.objects.create_user(
            email="mobile.corper@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        other_corper = ensure_corper_profile(other_user)
        other_corper.mobile_number = "08031234568"
        other_corper.save(update_fields=["mobile_number", "updated_at"])

        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.date_of_birth = "2001-06-15"
        corper.university_matriculation_number = "UNILAG/CSC/399"
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_number = "52345678901"
        corper.nysc_callup_number = "NYSC/BEN/2026/399999"
        corper.nysc_state_code = "NYSC/BE/26A/0995"
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nin_lookup_hash",
                "nysc_callup_number",
                "nysc_callup_lookup_hash",
                "nysc_state_code",
                "nysc_state_code_lookup_hash",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )
        photo = SimpleUploadedFile("profile-photo.jpg", b"fake-image-bytes", content_type="image/jpeg")

        response = self.client.patch(
            "/api/corpers/me/",
            {
                "posting_location_state": "Lagos",
                "batch": "Batch A",
                "stream": "Stream 1",
                "field_of_study": "Computer Science",
                "degree": "BSc",
                "university": "University of Lagos",
                "graduation_year": "2027",
                "profile_photo": photo,
                "mobile_number": "+2348031234568",
                "technical_skills": "Product Design",
                "soft_skills": "Communication",
                "languages_spoken": "English",
                "available_date": "2027-03-01",
                "bio": "Ready for NYSC placement.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Accept every required legal document before editing your corper profile.",
        )


class ProfileVerificationReviewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="AdminPass123!",
            role="admin",
            email_verified=True,
            is_staff=True,
        )
        self.corper_user = User.objects.create_user(
            email="corper@example.com",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.corper = ensure_corper_profile(self.corper_user)
        self.attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.PROFILE,
            submitted_value_masked="Profile details submitted",
        )
        self.client.force_authenticate(self.admin_user)

    def test_profile_review_approval_does_not_override_document_based_verification(self):
        response = self.client.post(
            f"/api/verification/attempts/{self.attempt.id}/review/",
            {"status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.attempt.refresh_from_db()
        self.corper.refresh_from_db()

        self.assertEqual(self.attempt.status, VerificationAttempt.Status.APPROVED)
        self.assertEqual(self.corper.verification_status, CorperProfile.VerificationStatus.PENDING)

    def test_admin_can_retrieve_verification_attempt_detail_with_user_email(self):
        response = self.client.get(f"/api/verification/attempts/{self.attempt.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.attempt.id))
        self.assertEqual(response.data["user_email"], self.corper_user.email)
        self.assertEqual(response.data["corper_name"], "")
        self.assertIsNone(response.data["reviewer_email"])

    def test_admin_can_retrieve_verification_attempt_detail_with_document_link(self):
        document = SimpleUploadedFile(
            "callup-letter.pdf",
            b"%PDF-1.4 fake callup",
            content_type="application/pdf",
        )
        attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
            submitted_value_masked="NY****************56",
            metadata={
                "document_name": "callup-letter.pdf",
                "document_path": "/media/corpers/verification-documents/callup/callup-letter.pdf",
            },
        )
        self.corper.nysc_callup_document = document
        self.corper.save(update_fields=["nysc_callup_document", "updated_at"])

        response = self.client.get(f"/api/verification/attempts/{attempt.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["document_name"], "callup-letter.pdf")
        self.assertEqual(
            response.data["document_url"],
            "/media/corpers/verification-documents/callup/callup-letter.pdf",
        )

    def test_biodata_review_approval_populates_profile_fields(self):
        biodata_attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
            submitted_value_masked="Ada Lovelace | 2001-06-15 | UN*******01",
            metadata={
                "full_name": "Ada Lovelace",
                "date_of_birth": "2001-06-15",
                "university_matriculation_number": "UNILAG/CSC/001",
            },
        )

        response = self.client.post(
            f"/api/verification/attempts/{biodata_attempt.id}/review/",
            {"status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper.refresh_from_db()

        self.assertEqual(
            self.corper.biodata_verification_status,
            CorperProfile.SensitiveStatus.VERIFIED,
        )
        self.assertEqual(self.corper.full_name, "Ada Lovelace")
        self.assertEqual(str(self.corper.date_of_birth), "2001-06-15")
        self.assertEqual(self.corper.university_matriculation_number, "UNILAG/CSC/001")

    def test_direct_overall_status_changes_are_normalized_to_document_based_status(self):
        self.corper.verification_status = CorperProfile.VerificationStatus.VERIFIED
        self.corper.save()

        self.corper.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(self.corper.verification_status, CorperProfile.VerificationStatus.PENDING)
        self.assertEqual(self.attempt.status, VerificationAttempt.Status.PENDING)
