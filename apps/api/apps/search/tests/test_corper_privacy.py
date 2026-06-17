from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.services import ensure_trial_subscription


class CorperPrivacySearchTests(APITestCase):
    def setUp(self):
        self.company_user = User.objects.create_user(
            email="talent@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )

        verified_corper_user = User.objects.create_user(
            email="verified@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        verified_corper = ensure_corper_profile(verified_corper_user)
        self.verified_corper = verified_corper
        verified_corper.full_name = "Ada Verified"
        verified_corper.date_of_birth = "2000-06-15"
        verified_corper.gender = CorperProfile.Gender.FEMALE
        verified_corper.posting_location_state = "Lagos"
        verified_corper.batch = CorperProfile.Batch.BATCH_A
        verified_corper.stream = CorperProfile.Stream.STREAM_1
        verified_corper.field_of_study = "Mathematics"
        verified_corper.degree = "B.Sc"
        verified_corper.university = "University of Lagos"
        verified_corper.university_matriculation_number = "UNILAG/MTH/001"
        verified_corper.graduation_year = 2024
        verified_corper.profile_photo = "corpers/profile-photos/verified.jpg"
        verified_corper.mobile_number = "08031234567"
        verified_corper.nin_number = "12345678901"
        verified_corper.nysc_callup_number = "NYSC/BEN/2024/123456"
        verified_corper.nysc_state_code = "NYSC/BE/24A/0123"
        verified_corper.skill = "Excel"
        verified_corper.technical_skills = "Excel"
        verified_corper.soft_skills = "Communication"
        verified_corper.languages_spoken = "English"
        verified_corper.available_date = "2026-01-01"
        verified_corper.bio = "Ready for deployment."
        verified_corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verified_corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verified_corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verified_corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        verified_corper.approval_status = CorperProfile.ApprovalStatus.APPROVED
        verified_corper.terms_of_agreement_accepted_at = timezone.now()
        verified_corper.terms_of_use_accepted_at = timezone.now()
        verified_corper.save()

        pending_corper_user = User.objects.create_user(
            email="pending@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        pending_corper = ensure_corper_profile(pending_corper_user)
        self.pending_corper = pending_corper
        pending_corper.full_name = "Bola Pending"
        pending_corper.date_of_birth = "1999-09-10"
        pending_corper.gender = CorperProfile.Gender.MALE
        pending_corper.posting_location_state = "Abuja"
        pending_corper.field_of_study = "Physics"
        pending_corper.degree = "B.Sc"
        pending_corper.university = "University of Ibadan"
        pending_corper.mobile_number = "08035550000"
        pending_corper.nysc_callup_number = "NYSC/FCT/2025/987654"
        pending_corper.skill = "Research"
        pending_corper.verification_status = CorperProfile.VerificationStatus.PENDING
        pending_corper.save()

    def test_company_search_corper_results_only_include_completed_profiles(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        returned_names = {result["full_name"] for result in response.data["results"]}
        self.assertEqual(returned_names, {"Ada Verified"})

    def test_public_search_corper_results_only_include_completed_profiles(self):
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        returned_names = {result["full_name"] for result in response.data["results"]}
        self.assertEqual(returned_names, {"Ada Verified"})

    def test_public_search_corpers_excludes_incomplete_profiles_from_filters(self):
        response = self.client.get("/api/search/corpers/", {"search": "Abuja"})

        self.assertEqual(response.status_code, 200)
        returned_names = {result["full_name"] for result in response.data["results"]}
        self.assertEqual(returned_names, set())

    def test_public_search_corpers_include_online_active_and_total_stats(self):
        self.verified_corper.user.last_seen_at = timezone.now()
        self.verified_corper.user.save(update_fields=["last_seen_at", "updated_at"])
        deleted_corper_user = User.objects.create_user(
            email="deleted@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        deleted_corper_user.delete()

        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["directory_stats"],
            {
                "online_count": 1,
                "active_count": 1,
                "total_count": 1,
            },
        )

    def test_public_search_corpers_expose_individual_online_status(self):
        self.verified_corper.user.last_seen_at = timezone.now()
        self.verified_corper.user.save(update_fields=["last_seen_at", "updated_at"])

        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        results = {result["full_name"]: result for result in response.data["results"]}
        self.assertTrue(results["Ada Verified"]["is_online"])

    def test_company_search_corpers_online_count_excludes_logged_out_corpers(self):
        self.verified_corper.user.last_seen_at = timezone.now()
        self.verified_corper.user.save(update_fields=["last_seen_at", "updated_at"])

        self.client.force_authenticate(self.verified_corper.user)
        logout_response = self.client.post("/api/auth/logout/", format="json")

        self.assertEqual(logout_response.status_code, 200)

        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["directory_stats"]["online_count"], 0)

    def test_company_search_corpers_expose_individual_online_status(self):
        self.verified_corper.user.last_seen_at = timezone.now()
        self.verified_corper.user.save(update_fields=["last_seen_at", "updated_at"])

        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        results = {result["full_name"]: result for result in response.data["results"]}
        self.assertTrue(results["Ada Verified"]["is_online"])

    def test_public_search_corpers_hides_recommendation_fields(self):
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        for result in response.data["results"]:
            self.assertIsNone(result["match_score"])
            self.assertEqual(result["match_reasons"], [])
            self.assertFalse(result["recommended"])

    def test_company_can_view_verified_corper_directory_detail(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get(f"/api/corpers/directory/{self.verified_corper.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["full_name"], "Ada Verified")
        self.assertEqual(response.data["email"], "verified@school.ng")
        self.assertEqual(response.data["nysc_service_year"], "2024")
        self.assertEqual(response.data["nysc_callup_number"], "NYSC/BEN/2024/123456")
        self.assertEqual(response.data["mobile_number"], "+2348031234567")
        self.assertFalse(response.data["company_interest_saved"])
        self.assertFalse(response.data["corper_has_expressed_interest"])
        self.assertFalse(response.data["corper_has_paid_access"])

    def test_company_cannot_view_incomplete_corper_directory_detail(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get(f"/api/corpers/directory/{self.pending_corper.id}/")

        self.assertEqual(response.status_code, 404)

    def test_company_search_hides_complete_but_unapproved_corper_profiles(self):
        complete_pending_user = User.objects.create_user(
            email="complete-pending@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_pending_corper = ensure_corper_profile(complete_pending_user)
        complete_pending_corper.full_name = "Complete Pending"
        complete_pending_corper.date_of_birth = "2000-01-10"
        complete_pending_corper.gender = CorperProfile.Gender.MALE
        complete_pending_corper.posting_location_state = "Lagos"
        complete_pending_corper.batch = CorperProfile.Batch.BATCH_B
        complete_pending_corper.stream = CorperProfile.Stream.STREAM_1
        complete_pending_corper.field_of_study = "Economics"
        complete_pending_corper.degree = "B.Sc"
        complete_pending_corper.university = "University of Ibadan"
        complete_pending_corper.university_matriculation_number = "UI/ECO/002"
        complete_pending_corper.graduation_year = 2024
        complete_pending_corper.profile_photo = "corpers/profile-photos/complete-pending.jpg"
        complete_pending_corper.mobile_number = "08035550001"
        complete_pending_corper.nin_number = "12345678902"
        complete_pending_corper.nysc_callup_number = "NYSC/LAG/2024/222222"
        complete_pending_corper.nysc_state_code = "NYSC/LA/24B/0222"
        complete_pending_corper.skill = "Finance"
        complete_pending_corper.technical_skills = "Finance"
        complete_pending_corper.soft_skills = "Analysis"
        complete_pending_corper.languages_spoken = "English"
        complete_pending_corper.available_date = "2026-01-01"
        complete_pending_corper.bio = "Waiting for approval."
        complete_pending_corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        complete_pending_corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        complete_pending_corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        complete_pending_corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        complete_pending_corper.terms_of_agreement_accepted_at = timezone.now()
        complete_pending_corper.terms_of_use_accepted_at = timezone.now()
        complete_pending_corper.save()

        self.client.force_authenticate(self.company_user)
        search_response = self.client.get("/api/search/corpers/")
        detail_response = self.client.get(f"/api/corpers/directory/{complete_pending_corper.id}/")

        self.assertEqual(search_response.status_code, 200)
        returned_names = {result["full_name"] for result in search_response.data["results"]}
        self.assertEqual(returned_names, {"Ada Verified"})
        self.assertEqual(detail_response.status_code, 404)

    def test_paused_corper_is_hidden_from_search_stats_and_detail(self):
        self.verified_corper.directory_visibility_paused = True
        self.verified_corper.save(update_fields=["directory_visibility_paused", "updated_at"])

        self.client.force_authenticate(self.company_user)
        search_response = self.client.get("/api/search/corpers/")
        detail_response = self.client.get(f"/api/corpers/directory/{self.verified_corper.id}/")

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.data["results"], [])
        self.assertEqual(
            search_response.data["directory_stats"],
            {
                "online_count": 0,
                "active_count": 0,
                "total_count": 0,
            },
        )
        self.assertEqual(detail_response.status_code, 404)

    def test_company_with_expired_trial_can_still_browse_corpers(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        returned_names = {result["full_name"] for result in response.data["results"]}
        self.assertEqual(returned_names, {"Ada Verified"})

    def test_company_with_expired_trial_can_still_view_corper_detail(self):
        self.client.force_authenticate(self.company_user)
        response = self.client.get(f"/api/corpers/directory/{self.verified_corper.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["full_name"], "Ada Verified")
