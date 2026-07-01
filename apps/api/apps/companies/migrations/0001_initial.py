import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company_name", models.CharField(max_length=255)),
                ("company_registration_number", models.CharField(max_length=120)),
                ("tax_identification_number", models.CharField(max_length=120)),
                ("company_image", models.FileField(blank=True, null=True, upload_to="companies/profile-images/")),
                ("company_location_state", models.CharField(max_length=500)),
                ("preferred_deployment_states", models.CharField(blank=True, default="", max_length=500)),
                ("company_location_city", models.CharField(max_length=120)),
                ("company_address", models.CharField(max_length=255)),
                ("head_office_address", models.CharField(blank=True, default="", max_length=255)),
                ("company_website", models.URLField(blank=True, default="", max_length=255)),
                ("company_sector", models.CharField(max_length=120)),
                ("organization_type", models.CharField(blank=True, default="", max_length=120)),
                ("staff_count_range", models.CharField(blank=True, default="", max_length=64)),
                ("ppa_capacity", models.PositiveIntegerField(blank=True, null=True)),
                ("office_location_count", models.PositiveIntegerField(blank=True, null=True)),
                ("company_function", models.CharField(max_length=120)),
                ("placement_type", models.CharField(blank=True, default="", max_length=64)),
                ("monthly_allowance_offered", models.CharField(blank=True, default="", max_length=64)),
                ("ppa_support", models.CharField(blank=True, default="", max_length=64)),
                ("desired_corper_description", models.TextField()),
                ("desired_qualification", models.TextField()),
                ("desired_age_range", models.CharField(max_length=64)),
                ("desired_field_of_study", models.TextField(default="")),
                ("desired_university", models.TextField(blank=True, default="")),
                ("desired_posting_states", models.CharField(blank=True, default="", max_length=500)),
                ("desired_skills", models.TextField()),
                ("desired_experience", models.TextField()),
                ("contact_name", models.CharField(blank=True, default="", max_length=255)),
                ("contact_email", models.EmailField(blank=True, default="", max_length=255)),
                ("contact_phone", models.CharField(blank=True, max_length=20)),
                ("directors_name", models.CharField(blank=True, default="", max_length=255)),
                ("director_phone_number", models.CharField(blank=True, default="", max_length=20)),
                ("terms_of_agreement_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("terms_of_use_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("legal_acceptances", models.JSONField(blank=True, default=dict)),
                ("directory_visibility_paused", models.BooleanField(default=False)),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("unsubmitted", "Unsubmitted"),
                            ("pending", "Pending"),
                            ("verified", "Verified"),
                            ("rejected", "Rejected"),
                        ],
                        default="unsubmitted",
                        max_length=20,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="company_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "companies_companyprofile",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["company_location_state", "company_location_city"],
                        name="company_profile_location_idx",
                    ),
                    models.Index(
                        fields=["company_sector", "company_function"],
                        name="company_profile_sector_fn_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=~Q(company_registration_number=""),
                        fields=("company_registration_number",),
                        name="companies_unique_reg_number",
                    ),
                    models.UniqueConstraint(
                        condition=~Q(tax_identification_number=""),
                        fields=("tax_identification_number",),
                        name="companies_unique_tax_number",
                    ),
                ],
            },
        ),
    ]
