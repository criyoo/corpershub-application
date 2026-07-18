from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.companies.models import CompanyProfile
from apps.companies.services import ensure_company_profile


User = get_user_model()


class CompanyProfileAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass123!",
        )
        self.company_user = User.objects.create_user(
            email="owner@company.ng",
            password="StrongPass123!",
            role=User.Role.COMPANY,
            email_verified=True,
        )
        self.company = ensure_company_profile(self.company_user)
        self.request = RequestFactory().get("/")
        self.request.user = self.superuser

    def test_company_profile_admin_uses_company_summary_label(self):
        admin_instance = admin.site._registry[CompanyProfile]

        form = admin_instance.get_form(self.request, obj=self.company)

        self.assertEqual(form.base_fields["desired_corper_description"].label, "Company summary")

    def test_company_profile_admin_exposes_completion_status(self):
        admin_instance = admin.site._registry[CompanyProfile]

        fields = admin_instance.get_fields(self.request, obj=self.company)

        self.assertIn("is_complete", fields)
