from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile


User = get_user_model()


class CorperProfileAdminTests(TestCase):
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
        self.corper = ensure_corper_profile(self.corper_user)
        self.corper.full_name = "Ada Admin"
        self.corper.posting_location_state = "Lagos"
        self.corper.batch = "Batch A"
        self.corper.stream = "Stream 1"
        self.corper.field_of_study = "Computer Science"
        self.corper.degree = "BSc"
        self.corper.university = "University of Lagos"
        self.corper.university_matriculation_number = "UNILAG/CSC/001"
        self.corper.mobile_number = "08031234567"
        self.corper.nysc_callup_number = "NYSC/BEN/2027/123456"
        self.corper.nysc_state_code = "NYSC/BE/27A/01234"
        self.corper.skill = "Python"
        self.corper.bio = "Ready for deployment."
        self.corper.save(
            update_fields=[
                "full_name",
                "posting_location_state",
                "batch",
                "stream",
                "field_of_study",
                "degree",
                "university",
                "university_matriculation_number",
                "mobile_number",
                "nysc_callup_number",
                "nysc_state_code",
                "skill",
                "bio",
                "updated_at",
            ]
        )
        self.request = RequestFactory().get("/")
        self.request.user = self.superuser

    def test_corper_profile_admin_uses_frontend_field_labels(self):
        admin_instance = admin.site._registry[CorperProfile]

        form = admin_instance.get_form(self.request, obj=self.corper)

        self.assertEqual(form.base_fields["posting_location_state"].label, "Posting state")
        self.assertEqual(form.base_fields["skill"].label, "Primary skill")

    def test_corper_profile_admin_exposes_completion_and_masked_values(self):
        admin_instance = admin.site._registry[CorperProfile]

        fields = admin_instance.get_fields(self.request, obj=self.corper)

        self.assertIn("gender", fields)
        self.assertIn("is_complete", fields)
        self.assertIn("masked_nin_number", fields)
        self.assertIn("nysc_service_year", fields)
        self.assertIn("masked_callup_number", fields)
        self.assertIn("masked_state_code", fields)

    def test_corper_profile_admin_exposes_editable_nysc_service_year_field(self):
        admin_instance = admin.site._registry[CorperProfile]
        form = admin_instance.get_form(self.request, obj=self.corper)

        self.assertIn("nysc_service_year", form.base_fields)
        self.assertNotIn("nysc_service_year", admin_instance.readonly_fields)
        self.assertEqual(form(instance=self.corper).fields["nysc_service_year"].initial, "2027")

    def test_corper_profile_admin_updates_callup_number_when_service_year_changes(self):
        admin_instance = admin.site._registry[CorperProfile]
        form_class = admin_instance.get_form(self.request, obj=self.corper)
        form = form_class(
            data={
                "user": str(self.corper_user.pk),
                "full_name": self.corper.full_name,
                "date_of_birth": "",
                "posting_location_state": self.corper.posting_location_state,
                "batch": self.corper.batch,
                "stream": self.corper.stream,
                "field_of_study": self.corper.field_of_study,
                "degree": self.corper.degree,
                "university": self.corper.university,
                "university_matriculation_number": self.corper.university_matriculation_number,
                "graduation_year": "",
                "profile_photo": "",
                "mobile_number": self.corper.mobile_number,
                "skill": self.corper.skill,
                "bio": self.corper.bio,
                "nin_number": "",
                "nysc_callup_number": self.corper.nysc_callup_number,
                "nysc_service_year": "2029",
            },
            instance=self.corper,
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated_corper = form.save()

        self.assertEqual(updated_corper.nysc_callup_number, "NYSC/BEN/2029/123456")
