from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CorperProfileApprovalFlowTests(APITestCase):
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
        self.corper = ensure_corper_profile(self.corper_user)
        self.corper.full_name = "Ada Lovelace"
        self.corper.date_of_birth = "2000-01-10"
        self.corper.posting_location_state = "Lagos"
        self.corper.batch = CorperProfile.Batch.BATCH_A
        self.corper.stream = CorperProfile.Stream.STREAM_1
        self.corper.field_of_study = "Computer Science"
        self.corper.degree = "B.Sc"
        self.corper.university = "University of Lagos"
        self.corper.graduation_year = 2024
        self.corper.profile_photo = "corpers/profile-photos/ada.jpg"
        self.corper.mobile_number = "+2348031234567"
        self.corper.nysc_callup_number = "NYSC/LAG/2024/123456"
        self.corper.nysc_state_code = "NYSC/LA/24A/0123"
        self.corper.skill = "Python"
        self.corper.technical_skills = "Python"
        self.corper.soft_skills = "Communication"
        self.corper.languages_spoken = "English"
        self.corper.available_date = "2026-06-01"
        self.corper.bio = "Ready for deployment."
        self.corper.terms_of_agreement_accepted_at = timezone.now()
        self.corper.terms_of_use_accepted_at = timezone.now()
        self.corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        self.corper.approval_status = CorperProfile.ApprovalStatus.PENDING
        self.corper.save()

    def test_admin_can_approve_completed_corper_and_send_welcome_email(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            f"/api/corpers/admin/{self.corper.id}/",
            {"approval_status": CorperProfile.ApprovalStatus.APPROVED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper.refresh_from_db()
        self.assertEqual(self.corper.approval_status, CorperProfile.ApprovalStatus.APPROVED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to corpershub", mail.outbox[0].subject)
