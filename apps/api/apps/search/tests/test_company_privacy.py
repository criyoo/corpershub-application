from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.companies.services import ensure_company_profile
from apps.interests.models import Interest
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end, ensure_trial_subscription
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


class CompanyPrivacySearchTests(APITestCase):
    def setUp(self):
        self.corper_user = User.objects.create_user(
            email="corper@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.corper_profile = ensure_corper_profile(self.corper_user)
        ensure_trial_subscription(user=self.corper_user)

        company_user = User.objects.create_user(
            email="talent@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.company_user = company_user
        company = ensure_company_profile(company_user)
        company.company_name = "Secret Ventures"
        company.company_address = "15 Hidden Road"
        company.company_location_state = "Lagos"
        company.company_location_city = "Lekki"
        company.company_sector = "Fintech"
        company.company_function = "Operations"
        company.desired_corper_description = "Structured NYSC placement."
        company.desired_qualification = "B.Sc / HND"
        company.desired_age_range = "21-29"
        company.desired_field_of_study = "Economics"
        company.desired_skills = "Communication, Excel"
        company.desired_experience = "Internship experience"
        company.verification_status = company.VerificationStatus.VERIFIED
        company.approval_status = company.ApprovalStatus.APPROVED
        company.save()
        self.company = company

    def test_corper_search_company_results_include_name_but_hide_address(self):
        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        result = response.data["results"][0]
        self.assertEqual(result["company_name"], "Secret Ventures")
        self.assertNotIn("company_address", result)
        self.assertEqual(result["company_sector"], "Fintech")
        self.assertEqual(result["location"], "Lekki, Lagos")

    def test_public_search_company_results_include_registered_companies(self):
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["company_name"], "Secret Ventures")

    def test_public_search_companies_include_online_active_and_total_stats(self):
        self.company_user.last_seen_at = timezone.now()
        self.company_user.save(update_fields=["last_seen_at", "updated_at"])
        deleted_company_user = User.objects.create_user(
            email="deleted@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        deleted_company_user.delete()

        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["directory_stats"],
            {
                "online_count": 1,
                "active_count": 1,
                "total_count": 1,
            },
        )

    def test_public_search_companies_stats_only_count_verified_company_profiles(self):
        pending_company_user = User.objects.create_user(
            email="pending@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        pending_company = ensure_company_profile(pending_company_user)
        pending_company.company_name = "Pending Company"
        pending_company.company_address = "2 Review Street"
        pending_company.company_location_state = "Lagos"
        pending_company.company_location_city = "Yaba"
        pending_company.company_sector = "Logistics"
        pending_company.company_function = "Support"
        pending_company.desired_corper_description = "Pending review."
        pending_company.desired_qualification = "B.Sc"
        pending_company.desired_age_range = "20-28"
        pending_company.desired_field_of_study = "Business Administration"
        pending_company.desired_skills = "Customer service"
        pending_company.desired_experience = "Entry level"
        pending_company.verification_status = pending_company.VerificationStatus.PENDING
        pending_company.save()
        pending_company_user.last_seen_at = timezone.now()
        pending_company_user.save(update_fields=["last_seen_at", "updated_at"])

        self.company_user.last_seen_at = timezone.now()
        self.company_user.save(update_fields=["last_seen_at", "updated_at"])

        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["directory_stats"],
            {
                "online_count": 1,
                "active_count": 1,
                "total_count": 1,
            },
        )

    def test_corper_search_companies_online_count_excludes_logged_out_companies(self):
        self.company_user.last_seen_at = timezone.now()
        self.company_user.save(update_fields=["last_seen_at", "updated_at"])

        self.client.force_authenticate(self.company_user)
        logout_response = self.client.post("/api/auth/logout/", format="json")

        self.assertEqual(logout_response.status_code, 200)

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["directory_stats"]["online_count"], 0)

    def test_corper_on_free_trial_does_not_see_match_scores(self):
        ensure_trial_subscription(user=self.corper_user)

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["results"][0]["match_score"])

    def test_corper_on_paid_plan_sees_match_scores(self):
        plan = SubscriptionPlan.objects.get(code=six)
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

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["results"][0]["match_score"])

    def test_public_search_companies_filters_by_city(self):
        response = self.client.get("/api/search/companies/", {"search": "Lekki"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["company_name"], "Secret Ventures")

    def test_public_search_companies_hides_recommendation_fields(self):
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        for result in response.data["results"]:
            self.assertIsNone(result["match_score"])
            self.assertEqual(result["match_reasons"], [])
            self.assertFalse(result["recommended"])

    def test_corper_can_view_verified_company_directory_detail_without_address(self):
        self.client.force_authenticate(self.corper_user)
        response = self.client.get(f"/api/companies/directory/{self.company.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company_name"], "Secret Ventures")
        self.assertEqual(response.data["summary_description"], "Structured NYSC placement.")
        self.assertEqual(response.data["desired_qualification"], "B.Sc / HND")
        self.assertEqual(response.data["desired_field_of_study"], "Economics")
        self.assertEqual(response.data["desired_skills"], "Communication, Excel")
        self.assertFalse(response.data["corper_has_expressed_interest"])
        self.assertFalse(response.data["company_has_expressed_interest"])
        self.assertNotIn("company_address", response.data)
        self.assertNotIn("contact_phone", response.data)

    def test_corper_company_directory_detail_marks_existing_interest(self):
        Interest.objects.create(
            corper=self.corper_profile,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.get(f"/api/companies/directory/{self.company.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["corper_has_expressed_interest"])
        self.assertFalse(response.data["company_has_expressed_interest"])

    def test_corper_company_directory_detail_marks_existing_company_interest(self):
        Interest.objects.create(
            corper=self.corper_profile,
            company=self.company,
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.get(f"/api/companies/directory/{self.company.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["corper_has_expressed_interest"])
        self.assertTrue(response.data["company_has_expressed_interest"])

    def test_corper_cannot_view_unverified_company_directory_detail(self):
        hidden_company_user = User.objects.create_user(
            email="hidden@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        hidden_company = ensure_company_profile(hidden_company_user)
        hidden_company.company_name = "Hidden Company"
        hidden_company.company_location_state = "Lagos"
        hidden_company.company_location_city = "Ikeja"
        hidden_company.company_address = "7 Invisible Street"
        hidden_company.company_sector = "Consulting"
        hidden_company.company_function = "Operations"
        hidden_company.desired_corper_description = "Private opening."
        hidden_company.desired_qualification = "B.Sc"
        hidden_company.desired_age_range = "22-28"
        hidden_company.desired_field_of_study = "Statistics"
        hidden_company.desired_skills = "Research"
        hidden_company.desired_experience = "Entry level"
        hidden_company.verification_status = hidden_company.VerificationStatus.PENDING
        hidden_company.save()

        self.client.force_authenticate(self.corper_user)
        response = self.client.get(f"/api/companies/directory/{hidden_company.id}/")

        self.assertEqual(response.status_code, 404)

    def test_paused_company_is_hidden_from_search_stats_and_detail(self):
        self.company.directory_visibility_paused = True
        self.company.save(update_fields=["directory_visibility_paused", "updated_at"])

        self.client.force_authenticate(self.corper_user)
        search_response = self.client.get("/api/search/companies/")
        detail_response = self.client.get(f"/api/companies/directory/{self.company.id}/")

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

    def test_corper_with_expired_trial_cannot_browse_companies(self):
        subscription = ensure_trial_subscription(user=self.corper_user)
        subscription.status = subscription.Status.TRIAL
        subscription.starts_at = timezone.now() - timedelta(days=8)
        subscription.ends_at = timezone.now() - timedelta(days=1)
        subscription.next_billing_at = subscription.ends_at
        subscription.save(update_fields=["status", "starts_at", "ends_at", "next_billing_at", "updated_at"])

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("free trial has expired", str(response.data["detail"]).lower())
