import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[("company", "Company"), ("corper", "Corper"), ("admin", "Admin")],
                        max_length=20,
                    ),
                ),
                ("email_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("deactivated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "deactivation_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "None"),
                            ("auto_expired_13_months", "Auto expired after 13 months"),
                            ("account_deleted", "Account deleted"),
                        ],
                        default="",
                        max_length=40,
                    ),
                ),
                ("reactivated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CompanyUser",
            fields=[],
            options={
                "verbose_name": "Company",
                "verbose_name_plural": "Companies",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("accounts.user",),
        ),
        migrations.CreateModel(
            name="CorperUser",
            fields=[],
            options={
                "verbose_name": "Corper",
                "verbose_name_plural": "Corpers",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("accounts.user",),
        ),
        migrations.CreateModel(
            name="DeletedAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("original_user_id", models.UUIDField(db_index=True)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                (
                    "role",
                    models.CharField(
                        choices=[("company", "Company"), ("corper", "Corper"), ("admin", "Admin")],
                        max_length=20,
                    ),
                ),
                ("full_name", models.CharField(blank=True, default="", max_length=255)),
                ("first_name", models.CharField(blank=True, default="", max_length=120)),
                ("surname", models.CharField(blank=True, default="", max_length=120)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("nin_lookup_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("deleted_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "ordering": ["-deleted_at"],
            },
        ),
        migrations.CreateModel(
            name="EmailDomainRule",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("domain", models.CharField(max_length=255, unique=True)),
                ("rule_type", models.CharField(choices=[("allowlist", "Allowlist"), ("denylist", "Denylist")], max_length=20)),
                ("note", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "ordering": ["domain"],
            },
        ),
        migrations.CreateModel(
            name="EmailOTP",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("signup", "Signup"),
                            ("password_reset", "Password Reset"),
                            ("company_password_change", "Company Password Change"),
                            ("company_email_change", "Company Email Change"),
                            ("company_mobile_change", "Company Mobile Change"),
                            ("company_delete_account", "Company Delete Account"),
                        ],
                        max_length=32,
                    ),
                ),
                ("code", models.CharField(max_length=8)),
                ("expires_at", models.DateTimeField()),
                ("last_sent_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_otps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PendingSignup",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[("company", "Company"), ("corper", "Corper"), ("admin", "Admin")],
                        max_length=20,
                    ),
                ),
                ("company_name", models.CharField(blank=True, default="", max_length=255)),
                ("company_registration_number", models.CharField(blank=True, default="", max_length=120)),
                ("subscription_plan_code", models.CharField(blank=True, default="", max_length=64)),
                ("password_hash", models.CharField(max_length=128)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserRoleRegistrationTotal",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("company", "Company"), ("corper", "Corper"), ("admin", "Admin")],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("total_registered", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["role"],
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role', 'email_verified'], name='accounts_us_role_6b0d1f_idx'),
        ),
        migrations.AddIndex(
            model_name="pendingsignup",
            index=models.Index(fields=["role", "-created_at"], name="accounts_pe_role_created_idx"),
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(fields=['email', 'purpose', '-created_at'], name='accounts_em_email_814cb4_idx'),
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(fields=['code', 'purpose'], name='accounts_em_code_b660c8_idx'),
        ),
        migrations.AddIndex(
            model_name="deletedaccount",
            index=models.Index(fields=["email", "-deleted_at"], name="accounts_deleted_email_idx"),
        ),
        migrations.AddIndex(
            model_name="deletedaccount",
            index=models.Index(
                fields=["first_name", "surname", "date_of_birth"],
                name="accounts_deleted_name_dob_idx",
            ),
        ),
    ]
