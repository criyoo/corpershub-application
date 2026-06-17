from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDPrimaryKeyModel
from apps.common.utils import generate_alphanumeric_code


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Role(models.TextChoices):
        COMPANY = "company", "Company"
        CORPER = "corper", "Corper"
        ADMIN = "admin", "Admin"

    class DeactivationReason(models.TextChoices):
        NONE = "", "None"
        AUTO_EXPIRED_13_MONTHS = "auto_expired_13_months", "Auto expired after 13 months"
        ACCOUNT_DELETED = "account_deleted", "Account deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(
        max_length=40,
        choices=DeactivationReason.choices,
        default=DeactivationReason.NONE,
        blank=True,
    )
    reactivated_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "email_verified"]),
        ]

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)
        if is_new and self.role in {self.Role.COMPANY, self.Role.CORPER}:
            counter, created = UserRoleRegistrationTotal.objects.get_or_create(
                role=self.role,
                defaults={"total_registered": 1},
            )
            if not created:
                UserRoleRegistrationTotal.objects.filter(pk=counter.pk).update(
                    total_registered=models.F("total_registered") + 1,
                    updated_at=timezone.now(),
                )

    @property
    def profile_completed(self) -> bool:
        if self.role == self.Role.COMPANY and hasattr(self, "company_profile"):
            return self.company_profile.is_complete
        if self.role == self.Role.CORPER and hasattr(self, "corper_profile"):
            return self.corper_profile.onboarding_complete
        return self.role == self.Role.ADMIN

    def __str__(self) -> str:
        return self.email


class CompanyUser(User):
    class Meta:
        proxy = True
        verbose_name = "Company"
        verbose_name_plural = "Companies"


class CorperUser(User):
    class Meta:
        proxy = True
        verbose_name = "Corper"
        verbose_name_plural = "Corpers"


class UserRoleRegistrationTotal(UUIDPrimaryKeyModel):
    role = models.CharField(max_length=20, choices=User.Role.choices, unique=True)
    total_registered = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["role"]

    def __str__(self) -> str:
        return f"{self.role}: {self.total_registered}"


class PendingSignup(UUIDPrimaryKeyModel):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=User.Role.choices)
    company_name = models.CharField(max_length=255, blank=True, default="")
    company_registration_number = models.CharField(max_length=120, blank=True, default="")
    subscription_plan_code = models.CharField(max_length=64, blank=True, default="")
    password_hash = models.CharField(max_length=128)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "-created_at"], name="accounts_pe_role_created_idx"),
        ]

    def __str__(self) -> str:
        return self.email


class EmailDomainRule(UUIDPrimaryKeyModel):
    class RuleType(models.TextChoices):
        ALLOWLIST = "allowlist", "Allowlist"
        DENYLIST = "denylist", "Denylist"

    domain = models.CharField(max_length=255, unique=True)
    rule_type = models.CharField(max_length=20, choices=RuleType.choices)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return f"{self.domain} ({self.rule_type})"


class EmailOTP(UUIDPrimaryKeyModel):
    class Purpose(models.TextChoices):
        SIGNUP = "signup", "Signup"
        ADMIN_REGISTRATION = "admin_registration", "Admin Registration"
        PASSWORD_RESET = "password_reset", "Password Reset"
        COMPANY_PASSWORD_CHANGE = "company_password_change", "Company Password Change"
        COMPANY_EMAIL_CHANGE = "company_email_change", "Company Email Change"
        COMPANY_MOBILE_CHANGE = "company_mobile_change", "Company Mobile Change"
        COMPANY_DELETE_ACCOUNT = "company_delete_account", "Company Delete Account"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    email = models.EmailField()
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField(default=timezone.now)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["email", "purpose", "consumed_at", "-created_at"],
                name="accounts_emailotp_active_idx",
            ),
        ]

    @classmethod
    def issue_code(
        cls,
        *,
        email: str,
        purpose: str,
        user=None,
        resend_window_seconds: int | None = None,
        expiry_seconds: int | None = None,
    ):
        existing = (
            cls.objects.filter(email=email, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        now = timezone.now()
        resend_window_seconds = resend_window_seconds or settings.OTP_RESEND_WINDOW_SECONDS
        expiry_seconds = expiry_seconds or settings.OTP_EXPIRY_SECONDS
        if existing and (now - existing.last_sent_at).total_seconds() < resend_window_seconds:
            raise ValidationError("Please wait before requesting another code.")

        raw_code = getattr(settings, "OTP_TEST_CODE", "") or generate_alphanumeric_code(6)
        otp = existing or cls(email=email, purpose=purpose, user=user)
        otp.user = user
        otp.code_hash = make_password(raw_code)
        otp.expires_at = now + timedelta(seconds=expiry_seconds)
        otp.last_sent_at = now
        otp.attempt_count = 0
        otp.verified_at = None
        otp.consumed_at = None
        otp.save()
        otp.raw_code = raw_code
        return otp

    def mark_verified(self):
        if self.verified_at is not None:
            return
        self.verified_at = timezone.now()
        self.save(update_fields=["verified_at", "updated_at"])

    def mark_consumed(self):
        current_time = timezone.now()
        update_fields = ["consumed_at", "updated_at"]
        self.consumed_at = current_time
        if self.verified_at is None:
            self.verified_at = current_time
            update_fields.insert(0, "verified_at")
        self.save(update_fields=update_fields)

    def invalidate(self):
        if self.consumed_at is not None:
            return
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at", "updated_at"])

    def matches_code(self, code: str) -> bool:
        normalized_code = (code or "").strip().upper()
        if len(normalized_code) != 6 or not normalized_code.isalnum():
            return False
        return check_password(normalized_code, self.code_hash)

    @property
    def has_exceeded_attempts(self) -> bool:
        return self.attempt_count >= settings.OTP_MAX_ATTEMPTS

    def register_failed_attempt(self):
        self.attempt_count += 1
        update_fields = ["attempt_count", "updated_at"]
        if self.attempt_count >= settings.OTP_MAX_ATTEMPTS and self.consumed_at is None:
            self.consumed_at = timezone.now()
            update_fields.insert(0, "consumed_at")
        self.save(update_fields=update_fields)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def clean(self):
        if not (self.code_hash or "").strip():
            raise ValidationError("OTP code hash is required.")


class DeletedAccount(UUIDPrimaryKeyModel):
    original_user_id = models.UUIDField(db_index=True)
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20, choices=User.Role.choices)
    full_name = models.CharField(max_length=255, blank=True, default="")
    first_name = models.CharField(max_length=120, blank=True, default="")
    surname = models.CharField(max_length=120, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    nin_lookup_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    deleted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-deleted_at"]
        indexes = [
            models.Index(fields=["email", "-deleted_at"], name="accounts_deleted_email_idx"),
            models.Index(
                fields=["first_name", "surname", "date_of_birth"],
                name="accounts_deleted_name_dob_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
