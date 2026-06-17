from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.corpers.models import CorperProfile
from apps.verification.models import CorperVerification, VerificationAttempt


User = get_user_model()


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class VerificationAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.corper_user = User.objects.create_user(
            email="corper@example.com",
            password="StrongPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        self.corper = CorperProfile.objects.create(
            user=self.corper_user,
            full_name="Ada Lovelace",
            posting_location_state="Lagos",
            field_of_study="Computer Science",
            degree="BSc",
            university="University of Lagos",
            mobile_number="08031234567",
            nysc_callup_number="NYSC/BEN/2027/123456",
            nysc_state_code="NYSC/BE/27A/0123",
            skill="Design",
        )
        self.request = RequestFactory().get("/")
        self.request.user = self.superuser
        self.client.force_login(self.superuser)

    def test_corper_profile_admin_form_excludes_verification_status_fields(self):
        admin_instance = admin.site._registry[CorperProfile]

        form = admin_instance.get_form(self.request, obj=self.corper)

        self.assertNotIn("verification_status", form.base_fields)
        self.assertNotIn("nin_verification_status", form.base_fields)
        self.assertNotIn("nysc_callup_verification_status", form.base_fields)

    def test_corper_profile_admin_uses_corper_labels(self):
        self.assertEqual(CorperProfile._meta.app_config.verbose_name, "Corpers")
        self.assertEqual(CorperProfile._meta.verbose_name, "Corper profile")
        self.assertEqual(CorperProfile._meta.verbose_name_plural, "Corpers profiles")

    def test_verification_admin_form_includes_status_fields(self):
        admin_instance = admin.site._registry[CorperVerification]
        verification = CorperVerification.objects.get(pk=self.corper.pk)

        form = admin_instance.get_form(self.request, obj=verification)

        self.assertNotIn("verification_status", form.base_fields)
        self.assertIn("biodata_verification_status", form.base_fields)
        self.assertIn("nin_verification_status", form.base_fields)
        self.assertIn("nysc_callup_verification_status", form.base_fields)
        self.assertIn("nysc_state_code_verification_status", form.base_fields)

    def test_verification_admin_changelist_is_available(self):
        response = self.client.get(reverse("admin:verification_corperverification_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "corper@example.com")
        self.assertContains(response, "User/Email")
        self.assertContains(response, 'value="delete_selected_verifications"')
        self.assertContains(response, 'class="action-checkbox"')

    def test_verification_page_updates_latest_attempt_statuses(self):
        nin_attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.NIN,
            submitted_value_masked="12*******01",
        )
        callup_attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
            submitted_value_masked="LA**********56",
        )

        verification = CorperVerification.objects.get(pk=self.corper.pk)
        verification.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nysc_callup_verification_status = CorperProfile.SensitiveStatus.REJECTED
        verification.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.save(
            update_fields=[
                "biodata_verification_status",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )

        nin_attempt.refresh_from_db()
        callup_attempt.refresh_from_db()

        self.assertEqual(nin_attempt.status, VerificationAttempt.Status.APPROVED)
        self.assertEqual(callup_attempt.status, VerificationAttempt.Status.REJECTED)
        self.assertEqual(
            verification.verification_status,
            CorperProfile.VerificationStatus.REJECTED,
        )

    def test_verified_documents_auto_mark_overall_verification_as_verified(self):
        verification = CorperVerification.objects.get(pk=self.corper.pk)
        verification.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.save(
            update_fields=[
                "biodata_verification_status",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )

        verification.refresh_from_db()

        self.assertEqual(
            verification.verification_status,
            CorperProfile.VerificationStatus.VERIFIED,
        )

    def test_approved_biodata_attempt_populates_profile_fields(self):
        self.corper.full_name = ""
        self.corper.date_of_birth = None
        self.corper.university_matriculation_number = ""
        self.corper.biodata_verification_status = CorperProfile.SensitiveStatus.UNSUBMITTED
        self.corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "updated_at",
            ]
        )

        attempt = VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
            submitted_value_masked="Ad*********ce | 2001-06-15 | UN*******01",
            metadata={
                "full_name": "Ada Lovelace",
                "date_of_birth": "2001-06-15",
                "university_matriculation_number": "UNILAG/CSC/001",
            },
        )

        attempt.status = VerificationAttempt.Status.APPROVED
        attempt.save(update_fields=["status", "updated_at"])

        self.corper.refresh_from_db()

        self.assertEqual(
            self.corper.biodata_verification_status,
            CorperProfile.SensitiveStatus.VERIFIED,
        )
        self.assertEqual(self.corper.full_name, "Ada Lovelace")
        self.assertEqual(str(self.corper.date_of_birth), "2001-06-15")
        self.assertEqual(self.corper.university_matriculation_number, "UNILAG/CSC/001")

    def test_verification_change_page_shows_pending_biodata_submission_values(self):
        self.corper.full_name = ""
        self.corper.date_of_birth = None
        self.corper.university_matriculation_number = ""
        self.corper.biodata_verification_status = CorperProfile.SensitiveStatus.PENDING
        self.corper.save(
            update_fields=[
                "full_name",
                "date_of_birth",
                "university_matriculation_number",
                "biodata_verification_status",
                "updated_at",
            ]
        )

        VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.BIODATA,
            submitted_value_masked="Ad*********ce | 2001-06-15 | UN*******01",
            metadata={
                "full_name": "Ada Lovelace",
                "date_of_birth": "2001-06-15",
                "university_matriculation_number": "UNILAG/CSC/001",
            },
        )

        response = self.client.get(reverse("admin:verification_corperverification_change", args=[self.corper.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, "2001-06-15")
        self.assertContains(response, "UNILAG/CSC/001")

    def test_verification_change_page_shows_uploaded_nysc_document_links(self):
        self.corper.nysc_callup_document = "corpers/verification-documents/callup/callup-letter.pdf"
        self.corper.nysc_state_code_document = "corpers/verification-documents/state-code/state-code-card.pdf"
        self.corper.save(update_fields=["nysc_callup_document", "nysc_state_code_document", "updated_at"])
        VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
            submitted_value_masked="LA**********56",
            metadata={
                "document_name": "callup-letter.pdf",
                "document_path": "/media/corpers/verification-documents/callup/callup-letter.pdf",
            },
        )

        response = self.client.get(reverse("admin:verification_corperverification_change", args=[self.corper.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View uploaded document")
        self.assertContains(response, "View submitted document")

    def test_rejected_document_auto_marks_overall_verification_as_rejected(self):
        verification = CorperVerification.objects.get(pk=self.corper.pk)
        verification.nin_verification_status = CorperProfile.SensitiveStatus.REJECTED
        verification.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verification.save(
            update_fields=[
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )

        verification.refresh_from_db()

        self.assertEqual(
            verification.verification_status,
            CorperProfile.VerificationStatus.REJECTED,
        )

    def test_bulk_delete_verifications_deletes_profiles_and_attempts(self):
        self.corper.verification_status = CorperProfile.VerificationStatus.VERIFIED
        self.corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.nin_number = "12345678901"
        self.corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.REJECTED
        self.corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.save(
            update_fields=[
                "verification_status",
                "biodata_verification_status",
                "nin_number",
                "nin_last4",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )
        VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.NIN,
            submitted_value_masked="12*******01",
            status=VerificationAttempt.Status.APPROVED,
        )
        VerificationAttempt.objects.create(
            corper=self.corper,
            verification_type=VerificationAttempt.VerificationType.CALLUP,
            submitted_value_masked="LA**********56",
            status=VerificationAttempt.Status.REJECTED,
        )

        response = self.client.post(
            reverse("admin:verification_corperverification_changelist"),
            {
                "action": "delete_selected_verifications",
                "_selected_action": [str(self.corper.pk)],
                "index": 0,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(CorperProfile.objects.filter(pk=self.corper.pk).exists())
        self.assertEqual(
            VerificationAttempt.objects.filter(corper_id=self.corper.pk).count(),
            0,
        )
