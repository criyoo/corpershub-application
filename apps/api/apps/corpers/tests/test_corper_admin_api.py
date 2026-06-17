from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile


class CorperAdminAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@corpershub.ng",
            password="AdminPass123!",
            role="admin",
            email_verified=True,
            is_staff=True,
        )
        self.corper_user = User.objects.create_user(
            email="corper@example.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_corper_profile_admin_list_omits_verification_status_fields(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.full_name = "Ada Lovelace"
        corper.university = "University of Lagos"
        corper.degree = "BSc"
        corper.verification_status = CorperProfile.VerificationStatus.VERIFIED
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save()

        response = self.client.get("/api/corpers/admin/")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["full_name"], "Ada Lovelace")
        self.assertNotIn("verification_status", result)
        self.assertNotIn("nin_verification_status", result)
        self.assertNotIn("nysc_callup_verification_status", result)
        self.assertNotIn("nysc_state_code_verification_status", result)

    def test_corper_verification_admin_list_includes_corper_without_profile(self):
        response = self.client.get("/api/corpers/admin/verifications/")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["email"], "corper@example.ng")
        self.assertEqual(result["full_name"], "")
        self.assertFalse(result["profile_created"])
        self.assertEqual(result["verification_status"], CorperProfile.VerificationStatus.PENDING)
        self.assertEqual(
            result["biodata_verification_status"],
            CorperProfile.SensitiveStatus.UNSUBMITTED,
        )
        self.assertEqual(
            result["nin_verification_status"],
            CorperProfile.SensitiveStatus.UNSUBMITTED,
        )
        self.assertEqual(
            result["nysc_callup_verification_status"],
            CorperProfile.SensitiveStatus.UNSUBMITTED,
        )
        self.assertEqual(
            result["nysc_state_code_verification_status"],
            CorperProfile.SensitiveStatus.UNSUBMITTED,
        )
        self.assertIsNone(result["nysc_callup_document"])
        self.assertIsNone(result["nysc_state_code_document"])

    def test_admin_can_update_corper_document_statuses_without_existing_profile(self):
        response = self.client.patch(
            f"/api/corpers/admin/verifications/{self.corper_user.id}/",
            {
                "nin_verification_status": CorperProfile.SensitiveStatus.VERIFIED,
                "nysc_callup_verification_status": CorperProfile.SensitiveStatus.REJECTED,
                "nysc_state_code_verification_status": CorperProfile.SensitiveStatus.VERIFIED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_user.refresh_from_db()
        self.assertTrue(hasattr(self.corper_user, "corper_profile"))
        self.assertEqual(
            self.corper_user.corper_profile.verification_status,
            CorperProfile.VerificationStatus.REJECTED,
        )
        self.assertEqual(
            self.corper_user.corper_profile.nin_verification_status,
            CorperProfile.SensitiveStatus.VERIFIED,
        )
        self.assertEqual(
            self.corper_user.corper_profile.nysc_callup_verification_status,
            CorperProfile.SensitiveStatus.REJECTED,
        )
        self.assertEqual(
            self.corper_user.corper_profile.nysc_state_code_verification_status,
            CorperProfile.SensitiveStatus.VERIFIED,
        )

    def test_corper_verification_admin_list_includes_uploaded_document_links(self):
        corper = ensure_corper_profile(self.corper_user)
        corper.nysc_callup_document = "corpers/verification-documents/callup/callup-letter.pdf"
        corper.nysc_state_code_document = "corpers/verification-documents/state-code/state-code-card.pdf"
        corper.save(update_fields=["nysc_callup_document", "nysc_state_code_document", "updated_at"])

        response = self.client.get("/api/corpers/admin/verifications/")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertIn("/media/corpers/verification-documents/callup/", result["nysc_callup_document"])
        self.assertIn(
            "/media/corpers/verification-documents/state-code/",
            result["nysc_state_code_document"],
        )
