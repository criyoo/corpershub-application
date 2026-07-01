import apps.common.fields
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
            name="CorperProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("full_name", models.CharField(max_length=255)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, choices=[("female", "Female"), ("male", "Male"), ("other", "Other")], default="", max_length=16)),
                ("posting_location_state", models.CharField(max_length=120)),
                ("batch", models.CharField(blank=True, choices=[("Batch A", "Batch A"), ("Batch B", "Batch B"), ("Batch C", "Batch C")], default="", max_length=20)),
                ("stream", models.CharField(blank=True, choices=[("Stream 1", "Stream 1"), ("Stream 2", "Stream 2")], default="", max_length=20)),
                ("field_of_study", models.CharField(max_length=255)),
                ("degree", models.CharField(max_length=120)),
                ("university", models.CharField(max_length=255)),
                ("university_matriculation_number", models.CharField(blank=True, default="", max_length=120)),
                ("graduation_year", models.PositiveIntegerField(blank=True, null=True)),
                ("profile_photo", models.FileField(blank=True, null=True, upload_to="corpers/profile-photos/")),
                ("nin_number", apps.common.fields.EncryptedCharField(blank=True)),
                ("nin_last4", models.CharField(blank=True, max_length=4)),
                ("nin_lookup_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("mobile_number", models.CharField(max_length=20)),
                ("nysc_callup_number", models.CharField(max_length=120)),
                ("nysc_callup_document", models.FileField(blank=True, null=True, upload_to="corpers/verification-documents/callup/")),
                ("nysc_callup_lookup_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("nysc_state_code", models.CharField(blank=True, default="", max_length=120)),
                ("nysc_state_code_document", models.FileField(blank=True, null=True, upload_to="corpers/verification-documents/state-code/")),
                ("nysc_state_code_lookup_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("skill", models.CharField(max_length=255)),
                ("technical_skills", models.CharField(blank=True, default="", max_length=255)),
                ("soft_skills", models.CharField(blank=True, default="", max_length=255)),
                ("languages_spoken", models.CharField(blank=True, default="", max_length=255)),
                ("available_date", models.DateField(blank=True, null=True)),
                ("bio", models.TextField(blank=True)),
                ("preferred_sector", models.CharField(blank=True, default="", max_length=120)),
                ("preferred_organization_type", models.CharField(blank=True, default="", max_length=120)),
                ("preferred_placement_type", models.CharField(blank=True, default="", max_length=120)),
                ("preferred_monthly_allowance", models.CharField(blank=True, default="", max_length=120)),
                ("preferred_organization_experience", models.TextField(blank=True)),
                ("terms_of_agreement_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("terms_of_use_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("legal_acceptances", models.JSONField(blank=True, default=dict)),
                ("verification_status", models.CharField(choices=[("pending", "Pending"), ("under_review", "Under Review"), ("verified", "Verified"), ("rejected", "Rejected")], default="pending", max_length=20)),
                ("biodata_verification_status", models.CharField(choices=[("unsubmitted", "Unsubmitted"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], default="unsubmitted", max_length=20)),
                ("nin_verification_status", models.CharField(choices=[("unsubmitted", "Unsubmitted"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], default="unsubmitted", max_length=20)),
                ("nysc_callup_verification_status", models.CharField(choices=[("unsubmitted", "Unsubmitted"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], default="unsubmitted", max_length=20)),
                ("nysc_state_code_verification_status", models.CharField(choices=[("unsubmitted", "Unsubmitted"), ("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], default="unsubmitted", max_length=20)),
                ("directory_visibility_paused", models.BooleanField(default=False)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="corper_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Corper profile",
                "verbose_name_plural": "Corpers profiles",
                "indexes": [
                    models.Index(fields=["posting_location_state"], name="corpers_cor_posting_efca05_idx"),
                    models.Index(fields=["field_of_study", "degree"], name="corpers_cor_field_o_8751ad_idx"),
                    models.Index(fields=["university", "graduation_year"], name="corpers_cor_univers_83ba43_idx"),
                    models.Index(fields=["skill"], name="corpers_cor_skill_f05174_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=~Q(university_matriculation_number=""),
                        fields=("university_matriculation_number",),
                        name="corpers_unique_matric_number",
                    ),
                    models.UniqueConstraint(
                        condition=~Q(mobile_number=""),
                        fields=("mobile_number",),
                        name="corpers_unique_mobile_number",
                    ),
                    models.UniqueConstraint(
                        condition=~Q(nin_lookup_hash=""),
                        fields=("nin_lookup_hash",),
                        name="corpers_unique_nin_hash",
                    ),
                    models.UniqueConstraint(
                        condition=~Q(nysc_callup_lookup_hash=""),
                        fields=("nysc_callup_lookup_hash",),
                        name="corpers_unique_callup_hash",
                    ),
                    models.UniqueConstraint(
                        condition=~Q(nysc_state_code_lookup_hash=""),
                        fields=("nysc_state_code_lookup_hash",),
                        name="corpers_unique_state_code_hash",
                    ),
                ],
            },
        ),
    ]
