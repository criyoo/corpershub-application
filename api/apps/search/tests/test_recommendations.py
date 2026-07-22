from datetime import date

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.companies.services import ensure_company_profile
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end


def years_ago(years: int) -> date:
    today = timezone.localdate()
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(month=2, day=28, year=today.year - years)


class CorperRecommendationSearchTests(APITestCase):
    def _make_discoverable(self, corper: CorperProfile, *, matric_no: str, photo: str, state_code: str):
        corper.batch = CorperProfile.Batch.BATCH_A
        corper.stream = CorperProfile.Stream.STREAM_1
        corper.university_matriculation_number = matric_no
        corper.profile_photo = photo
        corper.nysc_state_code = state_code

    def setUp(self):
        company_user = User.objects.create_user(
            email="talent@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        company = ensure_company_profile(company_user)
        company.company_name = "Prime Ops"
        company.company_location_state = "Lagos"
        company.company_location_city = "Ikeja"
        company.company_address = "19 Allen Avenue"
        company.company_sector = "Fintech"
        company.desired_corper_description = "Looking for organised corpers for operations analysis."
        company.desired_qualification = "B.Sc / HND"
        company.desired_age_range = "21-29"
        company.desired_field_of_study = "Business Administration"
        company.desired_university = "University of Lagos"
        company.desired_posting_states = "Lagos"
        company.desired_skills = "Excel, Communication, Analysis"
        company.desired_experience = "Spreadsheet reporting and operations support"
        company.placement_type = "Full-time / Hybrid"
        company.monthly_allowance_offered = "N50,000-N100,000"
        company.verification_status = company.VerificationStatus.VERIFIED
        company.save()
        self.company_user = company_user

        matched_corper_user = User.objects.create_user(
            email="matched@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        matched_corper = ensure_corper_profile(matched_corper_user)
        matched_corper.full_name = "Ada Match"
        matched_corper.date_of_birth = years_ago(24)
        matched_corper.gender = "female"
        matched_corper.posting_location_state = "Lagos"
        matched_corper.field_of_study = "Business Administration"
        matched_corper.degree = "B.Sc"
        matched_corper.university = "University of Lagos"
        matched_corper.graduation_year = timezone.localdate().year - 1
        matched_corper.mobile_number = "08031234567"
        matched_corper.nin_number = "12345678901"
        matched_corper.nysc_callup_number = "NYSC/LAG/2025/123456"
        matched_corper.skill = "Excel and communication"
        matched_corper.technical_skills = "Excel, Data Analysis"
        matched_corper.soft_skills = "Communication, Teamwork"
        matched_corper.languages_spoken = "English"
        matched_corper.available_date = timezone.localdate()
        matched_corper.bio = "Operations support and analysis experience."
        matched_corper.preferred_sector = "Fintech"
        matched_corper.preferred_placement_type = "Full-time / Hybrid"
        matched_corper.preferred_monthly_allowance = "N50,000-N100,000"
        matched_corper.preferred_organization_experience = "Spreadsheet reporting and operations support."
        self._make_discoverable(
            matched_corper,
            matric_no="UNILAG/BUS/001",
            photo="corpers/profile-photos/matched.jpg",
            state_code="NYSC/LA/25A/00101",
        )
        matched_corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        matched_corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        matched_corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        matched_corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        matched_corper.approval_status = CorperProfile.ApprovalStatus.APPROVED
        matched_corper.terms_of_agreement_accepted_at = timezone.now()
        matched_corper.terms_of_use_accepted_at = timezone.now()
        matched_corper.save()
        self.matched_corper = matched_corper

        close_corper_user = User.objects.create_user(
            email="close@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        close_corper = ensure_corper_profile(close_corper_user)
        close_corper.full_name = "Chika Close"
        close_corper.date_of_birth = years_ago(24)
        close_corper.gender = "female"
        close_corper.posting_location_state = "Lagos"
        close_corper.field_of_study = "Business Administration"
        close_corper.degree = "B.Sc"
        close_corper.university = "Lagos State University"
        close_corper.graduation_year = timezone.localdate().year - 2
        close_corper.mobile_number = "08037778889"
        close_corper.nin_number = "12345678902"
        close_corper.nysc_callup_number = "NYSC/LAG/2025/223355"
        close_corper.skill = "Customer relations"
        close_corper.technical_skills = "PowerPoint"
        close_corper.soft_skills = "Customer relations"
        close_corper.languages_spoken = "English"
        close_corper.available_date = timezone.localdate()
        close_corper.bio = "Reliable teammate with volunteer experience."
        close_corper.preferred_sector = "Business Services"
        close_corper.preferred_placement_type = "Part-Time / On-Site"
        close_corper.preferred_monthly_allowance = "Below N25,000"
        close_corper.preferred_organization_experience = "Volunteer support."
        self._make_discoverable(
            close_corper,
            matric_no="LASU/BUS/002",
            photo="corpers/profile-photos/close.jpg",
            state_code="NYSC/LA/25A/00202",
        )
        close_corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        close_corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        close_corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        close_corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        close_corper.approval_status = CorperProfile.ApprovalStatus.APPROVED
        close_corper.terms_of_agreement_accepted_at = timezone.now()
        close_corper.terms_of_use_accepted_at = timezone.now()
        close_corper.save()
        self.close_corper = close_corper

        secondary_corper_user = User.objects.create_user(
            email="secondary@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        secondary_corper = ensure_corper_profile(secondary_corper_user)
        secondary_corper.full_name = "Bola Mismatch"
        secondary_corper.date_of_birth = years_ago(31)
        secondary_corper.gender = "male"
        secondary_corper.posting_location_state = "Abuja"
        secondary_corper.field_of_study = "Fine Arts"
        secondary_corper.degree = "OND"
        secondary_corper.university = "Yaba College of Technology"
        secondary_corper.graduation_year = timezone.localdate().year - 3
        secondary_corper.mobile_number = "08039876543"
        secondary_corper.nin_number = "12345678903"
        secondary_corper.nysc_callup_number = "NYSC/FCT/2025/654321"
        secondary_corper.skill = "Illustration"
        secondary_corper.technical_skills = "Illustration, Branding"
        secondary_corper.soft_skills = "Creativity"
        secondary_corper.languages_spoken = "English"
        secondary_corper.available_date = timezone.localdate()
        secondary_corper.bio = "Creative design and studio work."
        secondary_corper.preferred_sector = "Design"
        secondary_corper.preferred_placement_type = "Part-Time / Remote"
        secondary_corper.preferred_monthly_allowance = "Above N100,000"
        secondary_corper.preferred_organization_experience = "Agency work."
        self._make_discoverable(
            secondary_corper,
            matric_no="YABATECH/ART/003",
            photo="corpers/profile-photos/secondary.jpg",
            state_code="NYSC/FC/25A/00303",
        )
        secondary_corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        secondary_corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        secondary_corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        secondary_corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        secondary_corper.approval_status = CorperProfile.ApprovalStatus.APPROVED
        secondary_corper.terms_of_agreement_accepted_at = timezone.now()
        secondary_corper.terms_of_use_accepted_at = timezone.now()
        secondary_corper.save()
        self.secondary_corper = secondary_corper

    def test_company_search_orders_corpers_by_recommendation_score(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.get("/api/search/corpers/")

        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(results[0]["id"], str(self.matched_corper.id))
        self.assertEqual(results[1]["id"], str(self.close_corper.id))
        self.assertGreater(results[0]["match_score"], results[1]["match_score"])
        self.assertGreater(len({result["match_score"] for result in results}), 1)
        self.assertTrue(results[0]["recommended"])
        self.assertTrue(
            any(
                "Qualification matches" in reason
                or "Technical skills matched" in reason
                or "Field of study" in reason
                or "University matches" in reason
                for reason in results[0]["match_reasons"]
            )
        )

    def test_corper_directory_detail_uses_same_recommendation_score(self):
        self.client.force_authenticate(self.company_user)

        list_response = self.client.get("/api/search/corpers/")
        self.assertEqual(list_response.status_code, 200)
        list_scores = {result["id"]: result["match_score"] for result in list_response.data["results"]}

        matched_response = self.client.get(f"/api/corpers/directory/{self.matched_corper.id}/")
        close_response = self.client.get(f"/api/corpers/directory/{self.close_corper.id}/")

        self.assertEqual(matched_response.status_code, 200)
        self.assertEqual(close_response.status_code, 200)
        self.assertEqual(
            matched_response.data["match_score"],
            list_scores[str(self.matched_corper.id)],
        )
        self.assertEqual(
            close_response.data["match_score"],
            list_scores[str(self.close_corper.id)],
        )
        self.assertGreater(
            matched_response.data["match_score"],
            close_response.data["match_score"],
        )

    def test_company_search_filters_corpers_by_age_range_and_gender(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.get("/api/search/corpers/", {"search": "female 23-25"})

        self.assertEqual(response.status_code, 200)
        returned_ids = [result["id"] for result in response.data["results"]]
        self.assertEqual(returned_ids, [str(self.matched_corper.id), str(self.close_corper.id)])

    def test_company_search_filters_corpers_by_graduation_year_range(self):
        self.client.force_authenticate(self.company_user)

        current_year = timezone.localdate().year
        response = self.client.get(
            "/api/search/corpers/",
            {"search": f"{current_year - 2}-{current_year - 1}"},
        )

        self.assertEqual(response.status_code, 200)
        returned_ids = {result["id"] for result in response.data["results"]}
        self.assertEqual(
            returned_ids,
            {str(self.matched_corper.id), str(self.close_corper.id)},
        )


class CompanyRecommendationSearchTests(APITestCase):
    def setUp(self):
        corper_user = User.objects.create_user(
            email="corper@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        corper = ensure_corper_profile(corper_user)
        corper.full_name = "Tobi Corper"
        corper.date_of_birth = years_ago(23)
        corper.posting_location_state = "Lagos"
        corper.field_of_study = "Economics"
        corper.degree = "B.Sc"
        corper.university = "University of Ibadan"
        corper.graduation_year = timezone.localdate().year - 1
        corper.mobile_number = "08035551234"
        corper.nysc_callup_number = "NYSC/LAG/2025/223344"
        corper.skill = "Excel, analysis, reporting"
        corper.technical_skills = "Excel, Reporting"
        corper.soft_skills = "Communication, Teamwork"
        corper.languages_spoken = "English"
        corper.available_date = timezone.localdate()
        corper.bio = "Interested in operations and finance roles."
        corper.preferred_sector = "Finance"
        corper.preferred_placement_type = "Full-time / Hybrid"
        corper.preferred_monthly_allowance = "N50,000-N100,000"
        corper.preferred_organization_experience = "Operations analysis"
        corper.save()
        self.corper_user = corper_user
        paid_plan = SubscriptionPlan.objects.filter(price_kobo__gt=0).order_by("price_kobo").first()
        starts_at = timezone.now()
        ends_at = calculate_subscription_end(plan=paid_plan, starts_at=starts_at)
        UserSubscription.objects.create(
            user=self.corper_user,
            plan=paid_plan,
            status=UserSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
            is_auto_renew=False,
            metadata={"source": "test"},
        )

        matching_company_user = User.objects.create_user(
            email="matching@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        matching_company = ensure_company_profile(matching_company_user)
        matching_company.company_name = "Lagos Finance Hub"
        matching_company.company_location_state = "Lagos"
        matching_company.company_location_city = "Yaba"
        matching_company.company_address = "12 Herbert Macaulay"
        matching_company.company_sector = "Finance"
        matching_company.desired_corper_description = "Finance operations and reporting support."
        matching_company.desired_qualification = "B.Sc"
        matching_company.desired_age_range = "21-28"
        matching_company.desired_field_of_study = "Economics"
        matching_company.desired_university = "University of Ibadan"
        matching_company.desired_posting_states = "Ogun, Lagos"
        matching_company.desired_skills = "Excel, Reporting"
        matching_company.desired_experience = "Operations analysis"
        matching_company.placement_type = "Full-time / Hybrid"
        matching_company.monthly_allowance_offered = "N50,000-N100,000"
        matching_company.verification_status = matching_company.VerificationStatus.VERIFIED
        matching_company.approval_status = matching_company.ApprovalStatus.APPROVED
        matching_company.save()
        self.matching_company = matching_company

        close_company_user = User.objects.create_user(
            email="close@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        close_company = ensure_company_profile(close_company_user)
        close_company.company_name = "Lagos Shared Services"
        close_company.company_location_state = "Lagos"
        close_company.company_location_city = "Surulere"
        close_company.company_address = "2 Bode Thomas"
        close_company.company_sector = "Business Services"
        close_company.desired_corper_description = "Need dependable corpers for structured office work."
        close_company.desired_qualification = "B.Sc"
        close_company.desired_age_range = "21-28"
        close_company.desired_field_of_study = "Economics"
        close_company.desired_university = "University of Lagos"
        close_company.desired_posting_states = "Lagos"
        close_company.desired_skills = "PowerPoint, Teamwork"
        close_company.desired_experience = "Community outreach"
        close_company.placement_type = "Part-Time / On-Site"
        close_company.monthly_allowance_offered = "Below N25,000"
        close_company.verification_status = close_company.VerificationStatus.VERIFIED
        close_company.approval_status = close_company.ApprovalStatus.APPROVED
        close_company.save()
        self.close_company = close_company

        secondary_company_user = User.objects.create_user(
            email="secondary@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        secondary_company = ensure_company_profile(secondary_company_user)
        secondary_company.company_name = "Northern Design Studio"
        secondary_company.company_location_state = "Kaduna"
        secondary_company.company_location_city = "Kaduna"
        secondary_company.company_address = "44 Creative Close"
        secondary_company.company_sector = "Design"
        secondary_company.desired_corper_description = "Creative interns for studio support."
        secondary_company.desired_qualification = "OND"
        secondary_company.desired_age_range = "30+"
        secondary_company.desired_field_of_study = "Fine Arts"
        secondary_company.desired_university = "Yaba College of Technology"
        secondary_company.desired_posting_states = "Kaduna"
        secondary_company.desired_skills = "Illustration, Branding"
        secondary_company.desired_experience = "Agency work"
        secondary_company.placement_type = "Part-Time / Remote"
        secondary_company.monthly_allowance_offered = "Above N100,000"
        secondary_company.verification_status = secondary_company.VerificationStatus.VERIFIED
        secondary_company.approval_status = secondary_company.ApprovalStatus.APPROVED
        secondary_company.save()
        self.secondary_company = secondary_company

    def test_corper_search_orders_companies_by_recommendation_score(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(results[0]["id"], str(self.matching_company.id))
        self.assertEqual(results[1]["id"], str(self.close_company.id))
        self.assertGreater(results[0]["match_score"], results[1]["match_score"])
        self.assertGreater(len({result["match_score"] for result in results}), 1)
        self.assertTrue(results[0]["recommended"])
        self.assertTrue(
            any(
                "Your qualification matches" in reason
                or "Requested technical skills matched" in reason
                or "Located in your posting state" in reason
                or "Your university matches" in reason
                for reason in results[0]["match_reasons"]
            )
        )

    def test_corper_search_matches_company_when_state_is_in_multi_state_list(self):
        self.matching_company.company_location_state = "Ogun, Lagos"
        self.matching_company.save(update_fields=["company_location_state", "updated_at"])

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/search/companies/")

        self.assertEqual(response.status_code, 200)
        results = response.data["results"]
        self.assertEqual(results[0]["id"], str(self.matching_company.id))
        self.assertTrue(any("Located in your posting state" in reason for reason in results[0]["match_reasons"]))

    def test_company_directory_detail_uses_same_recommendation_score(self):
        self.client.force_authenticate(self.corper_user)

        list_response = self.client.get("/api/search/companies/")
        self.assertEqual(list_response.status_code, 200)
        list_scores = {result["id"]: result["match_score"] for result in list_response.data["results"]}

        matched_response = self.client.get(f"/api/companies/directory/{self.matching_company.id}/")
        close_response = self.client.get(f"/api/companies/directory/{self.close_company.id}/")

        self.assertEqual(matched_response.status_code, 200)
        self.assertEqual(close_response.status_code, 200)
        self.assertEqual(
            matched_response.data["match_score"],
            list_scores[str(self.matching_company.id)],
        )
        self.assertEqual(
            close_response.data["match_score"],
            list_scores[str(self.close_company.id)],
        )
        self.assertGreater(
            matched_response.data["match_score"],
            close_response.data["match_score"],
        )
