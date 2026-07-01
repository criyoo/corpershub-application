from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.companies.services import ensure_company_profile
from apps.interests.models import Interest
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end
from apps.chat.models import Message

free, three, six, twelve = billing_plans.keys()


class ChatFlowTests(APITestCase):
    def setUp(self):
        self.corper_user = User.objects.create_user(
            email="corper@school.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.corper = ensure_corper_profile(self.corper_user)
        self.corper.full_name = "Ada Corpers"
        self.corper.degree = "BSc"
        self.corper.field_of_study = "Computer Science"
        self.corper.profile_photo = "corpers/profile-photos/ada.jpg"
        self.corper.save(update_fields=["full_name", "degree", "field_of_study", "profile_photo", "updated_at"])

        self.company_user = User.objects.create_user(
            email="talent@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.company = ensure_company_profile(self.company_user)
        self.company.company_name = "Bright Future Logistics"
        self.company.company_image = "companies/profile-images/bright-future.jpg"
        self.company.save(update_fields=["company_name", "company_image", "updated_at"])

    def activate_paid_corper_plan(self):
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

    def test_company_cannot_initiate_chat_without_showing_interest(self):
        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"corper_id": str(self.corper.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Please indicate intereset in corper before initiating chat",
        )

    def test_company_cannot_initiate_chat_for_free_trial_corper(self):
        Interest.objects.create(
            corper=self.corper,
            company=self.company,
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"corper_id": str(self.corper.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("active paid plan", str(response.data["detail"]).lower())

    def test_company_cannot_initiate_chat_directly_until_it_marks_interest(self):
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"corper_id": str(self.corper.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Please indicate intereset in corper before initiating chat",
        )

        interest.refresh_from_db()
        self.assertIsNotNone(interest.corper_expressed_at)
        self.assertIsNone(interest.company_expressed_at)

    def test_company_can_initiate_chat_from_corper_interest(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["counterpart"]["name"], self.corper.full_name)
        self.assertEqual(response.data["counterpart"]["qualification"], "BSc · Computer Science")
        self.assertEqual(response.data["counterpart"]["image"], "/media/corpers/profile-photos/ada.jpg")
        self.assertEqual(response.data["participant_labels"]["corper"], "Ada")
        self.assertEqual(response.data["participant_labels"]["company"], "BFL")

    def test_conversation_detail_includes_participant_labels(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        initiate_response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )

        detail_response = self.client.get(f"/api/chat/conversations/{initiate_response.data['id']}/")

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["participant_labels"]["corper"], "Ada")
        self.assertEqual(detail_response.data["participant_labels"]["company"], "BFL")
        self.assertEqual(detail_response.data["participant_names"]["corper"], "Ada Corpers")
        self.assertEqual(detail_response.data["participant_names"]["company"], "Bright Future Logistics")
        self.assertEqual(detail_response.data["participant_images"]["corper"], "/media/corpers/profile-photos/ada.jpg")
        self.assertEqual(
            detail_response.data["participant_images"]["company"], "/media/companies/profile-images/bright-future.jpg"
        )

    def test_corper_conversation_list_includes_company_image(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/chat/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["results"][0]["counterpart"]["image"], "/media/companies/profile-images/bright-future.jpg"
        )

    def test_free_trial_corper_cannot_open_chat_list(self):
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.company_user)
        self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )

        UserSubscription.objects.filter(user=self.corper_user).delete()

        self.client.force_authenticate(self.corper_user)
        response = self.client.get("/api/chat/conversations/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("paid plans only", str(response.data["detail"]).lower())

    def test_company_conversation_list_includes_corper_qualification(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )
        response = self.client.get("/api/chat/conversations/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["counterpart"]["qualification"], "BSc · Computer Science")
        self.assertEqual(response.data["results"][0]["counterpart"]["degree"], "BSc")
        self.assertEqual(response.data["results"][0]["counterpart"]["field_of_study"], "Computer Science")

    def test_company_shortlist_allows_chat(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"corper_id": str(self.corper.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["interest"]), str(interest.id))

    def test_corper_cannot_initiate_chat_without_showing_interest(self):
        self.activate_paid_corper_plan()
        self.client.force_authenticate(self.corper_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"company_id": str(self.company.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Please indicate intereset in company before initiating chat",
        )

    def test_corper_cannot_initiate_chat_until_company_responds(self):
        self.activate_paid_corper_plan()
        Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"company_id": str(self.company.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"],
            "Please wait for company to indicate intereset before initiating chat",
        )

    def test_corper_can_initiate_chat_after_mutual_interest(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
            company_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.corper_user)
        response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"company_id": str(self.company.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["interest"]), str(interest.id))
        self.assertEqual(response.data["counterpart"]["name"], self.company.company_name)

    def test_mark_read_endpoint_clears_unread_count_immediately(self):
        self.activate_paid_corper_plan()
        interest = Interest.objects.create(
            corper=self.corper,
            company=self.company,
            corper_expressed_at=timezone.now(),
        )

        self.client.force_authenticate(self.company_user)
        initiate_response = self.client.post(
            "/api/chat/conversations/initiate/",
            {"interest_id": str(interest.id)},
            format="json",
        )
        conversation_id = initiate_response.data["id"]

        Message.objects.create(
            conversation_id=conversation_id,
            sender=self.company_user,
            content="Hello from the company",
        )

        self.client.force_authenticate(self.corper_user)
        list_response = self.client.get("/api/chat/conversations/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["results"][0]["unread_count"], 1)

        mark_read_response = self.client.post(
            f"/api/chat/conversations/{conversation_id}/mark-read/",
            format="json",
        )
        self.assertEqual(mark_read_response.status_code, 200)
        self.assertEqual(mark_read_response.data["unread_count"], 0)

        refreshed_list_response = self.client.get("/api/chat/conversations/")
        self.assertEqual(refreshed_list_response.status_code, 200)
        self.assertEqual(refreshed_list_response.data["results"][0]["unread_count"], 0)
