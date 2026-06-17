from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.models import DeletedAccount, EmailDomainRule, EmailOTP, PendingSignup, User
from apps.accounts.tasks import deliver_otp_email, send_otp_email_task
from apps.audit.services import log_audit_event
from apps.companies.services import ensure_company_profile
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.corpers.models import hash_sensitive_identifier
from apps.corpers.services import ensure_corper_profile

logger = logging.getLogger(__name__)
PASSWORD_RESET_TOKEN_SALT = "accounts.password_reset"
PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS = 60 * 15
DELETED_EMAIL_DOMAIN = "deleted.corpershub.local"
PENDING_SIGNUP_TTL = timezone.timedelta(days=7)


class OTPEmailDeliveryError(APIException):
    status_code = 503
    default_detail = "Unable to deliver the verification email right now. Check SMTP settings and try again."
    default_code = "otp_email_delivery_failed"


COMPANY_SETTINGS_OTP_PURPOSES = {
    "change_password": EmailOTP.Purpose.COMPANY_PASSWORD_CHANGE,
    "change_email": EmailOTP.Purpose.COMPANY_EMAIL_CHANGE,
    "change_mobile_number": EmailOTP.Purpose.COMPANY_MOBILE_CHANGE,
    "delete_account": EmailOTP.Purpose.COMPANY_DELETE_ACCOUNT,
}


def split_person_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in str(full_name or "").strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def deleted_account_email_exists(email: str) -> bool:
    normalized_email = User.objects.normalize_email(email)
    return DeletedAccount.objects.filter(email=normalized_email).exists()


def deleted_account_biodata_exists(*, full_name: str, date_of_birth) -> bool:
    first_name, surname = split_person_name(full_name)
    if not first_name or not surname or not date_of_birth:
        return False
    return DeletedAccount.objects.filter(
        role=User.Role.CORPER,
        first_name__iexact=first_name,
        surname__iexact=surname,
        date_of_birth=date_of_birth,
    ).exists()


def deleted_account_nin_exists(nin_number: str) -> bool:
    normalized = str(nin_number or "").strip()
    if not normalized:
        return False
    return DeletedAccount.objects.filter(nin_lookup_hash=hash_sensitive_identifier(normalized)).exists()


def get_company_settings_otp_purpose(action: str) -> str:
    try:
        return COMPANY_SETTINGS_OTP_PURPOSES[action]
    except KeyError as exc:
        raise ValidationError("Unsupported company settings verification action.") from exc


def issue_company_settings_otp(*, user: User, action: str, email: str) -> EmailOTP:
    purpose = get_company_settings_otp_purpose(action)
    try:
        otp = EmailOTP.issue_code(email=email, purpose=purpose, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc)) from exc
    dispatch_otp_email(email=email, code=otp.raw_code, purpose=purpose)
    log_audit_event(
        actor=user,
        action="auth.company_settings_otp_issued",
        target_type="user",
        target_id=str(user.id),
        metadata={"action": action, "email": email},
    )
    return otp


def consume_company_settings_otp(*, user: User, action: str, email: str, code: str) -> EmailOTP:
    purpose = get_company_settings_otp_purpose(action)
    otp = consume_valid_otp(email=email, code=code, purpose=purpose)
    if otp.user_id != user.id:
        raise ValidationError("Invalid or expired code.")
    return otp


def build_deleted_user_email(user: User) -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"deleted-{str(user.id).replace('-', '')[:16]}-{timestamp}@{DELETED_EMAIL_DOMAIN}"


def archive_deleted_user(*, user: User) -> DeletedAccount:
    full_name = ""
    first_name = ""
    surname = ""
    date_of_birth = None
    nin_lookup_hash = ""
    metadata: dict[str, Any] = {"deleted_by_user": True}

    if user.role == User.Role.CORPER:
        corper = ensure_corper_profile(user)
        full_name = corper.full_name or ""
        first_name, surname = split_person_name(full_name)
        date_of_birth = corper.date_of_birth
        nin_lookup_hash = corper.nin_lookup_hash or ""
        metadata.update(
            {
                "profile_id": str(corper.id),
                "posting_location_state": corper.posting_location_state,
                "university_matriculation_number": corper.university_matriculation_number,
            }
        )
    elif user.role == User.Role.COMPANY:
        company = ensure_company_profile(user)
        full_name = company.company_name or ""
        metadata.update(
            {
                "profile_id": str(company.id),
                "company_registration_number": company.company_registration_number,
                "tax_identification_number": company.tax_identification_number,
            }
        )

    deleted_account = DeletedAccount.objects.create(
        original_user_id=user.id,
        email=User.objects.normalize_email(user.email),
        role=user.role,
        full_name=full_name,
        first_name=first_name,
        surname=surname,
        date_of_birth=date_of_birth,
        nin_lookup_hash=nin_lookup_hash,
        metadata=metadata,
        deleted_at=timezone.now(),
    )

    user.email = build_deleted_user_email(user)
    user.email_verified = False
    user.is_active = False
    user.deactivated_at = timezone.now()
    user.deactivation_reason = User.DeactivationReason.ACCOUNT_DELETED
    user.set_unusable_password()
    user.save(
        update_fields=[
            "email",
            "email_verified",
            "is_active",
            "deactivated_at",
            "deactivation_reason",
            "password",
            "updated_at",
        ]
    )
    return deleted_account


def validate_company_registration_email(email: str) -> None:
    domain = email.split("@")[-1].lower()
    denylisted = EmailDomainRule.objects.filter(
        domain=domain, rule_type=EmailDomainRule.RuleType.DENYLIST
    ).exists()
    if denylisted:
        raise ValidationError("This company email domain is not allowed.")

    allowlisted = EmailDomainRule.objects.filter(
        domain=domain, rule_type=EmailDomainRule.RuleType.ALLOWLIST
    ).exists()
    testing_exception = domain in getattr(settings, "COMPANY_EMAIL_TEST_ALLOWLIST", set())
    if domain in settings.FREE_EMAIL_PROVIDERS and not allowlisted and not testing_exception:
        raise ValidationError("Companies must register with a custom-domain email address.")


def create_or_update_pending_signup(
    *,
    email: str,
    password: str,
    role: str,
    company_name: str = "",
    company_registration_number: str = "",
    subscription_plan_code: str = "",
) -> PendingSignup:
    prune_expired_pending_signups(email=email)
    pending_signup, _ = PendingSignup.objects.get_or_create(email=email)
    pending_signup.role = role
    pending_signup.company_name = company_name.strip() if role == User.Role.COMPANY else ""
    pending_signup.company_registration_number = (
        company_registration_number.strip() if role == User.Role.COMPANY else ""
    )
    pending_signup.subscription_plan_code = ""
    pending_signup.password_hash = make_password(password)
    pending_signup.save()
    return pending_signup


def prune_expired_pending_signups(*, email: str | None = None) -> int:
    cutoff = timezone.now() - PENDING_SIGNUP_TTL
    expired_signups = PendingSignup.objects.filter(created_at__lt=cutoff)
    if email:
        expired_signups = expired_signups.filter(email=User.objects.normalize_email(email).strip())

    expired_emails = list(expired_signups.values_list("email", flat=True))
    deleted_count, _ = expired_signups.delete()
    if expired_emails:
        EmailOTP.objects.filter(email__in=expired_emails, purpose=EmailOTP.Purpose.SIGNUP).delete()
    return deleted_count


def issue_signup_otp(
    *,
    email: str,
    user: User | None = None,
    target_type: str = "pending_signup",
    target_id: str = "",
    metadata: dict[str, Any] | None = None,
):
    normalized_email = User.objects.normalize_email(email).strip()
    try:
        otp = EmailOTP.issue_code(email=normalized_email, purpose=EmailOTP.Purpose.SIGNUP, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc)) from exc
    dispatch_otp_email(
        email=normalized_email,
        code=otp.raw_code,
        purpose=EmailOTP.Purpose.SIGNUP,
    )
    audit_metadata = {"purpose": EmailOTP.Purpose.SIGNUP}
    if metadata:
        audit_metadata.update(metadata)
    log_audit_event(
        actor=user,
        action="auth.otp_issued",
        target_type=target_type,
        target_id=target_id or (str(user.id) if user else ""),
        metadata=audit_metadata,
    )
    return otp


def issue_password_reset_otp(*, user: User):
    normalized_email = User.objects.normalize_email(user.email).strip()
    try:
        otp = EmailOTP.issue_code(email=normalized_email, purpose=EmailOTP.Purpose.PASSWORD_RESET, user=user)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc)) from exc
    dispatch_otp_email(
        email=normalized_email,
        code=otp.raw_code,
        purpose=EmailOTP.Purpose.PASSWORD_RESET,
    )
    log_audit_event(
        actor=user,
        action="auth.password_reset_otp_issued",
        target_type="user",
        target_id=str(user.id),
    )
    return otp


def dispatch_otp_email(*, email: str, code: str, purpose: str) -> bool:
    try:
        if getattr(settings, "OTP_EMAIL_ASYNC", False):
            send_otp_email_task.delay(email, code, purpose)
            return True
        deliver_otp_email(email, code, purpose)
        return True
    except Exception as exc:
        logger.exception(
            "OTP email dispatch failed",
            extra={"email": email, "purpose": purpose},
        )
        raise OTPEmailDeliveryError() from exc


def get_valid_otp(*, email: str, code: str, purpose: str) -> EmailOTP:
    normalized_email = User.objects.normalize_email(email).strip()
    normalized_code = code.strip().upper()
    otp = (
        EmailOTP.objects.select_related("user")
        .filter(email=normalized_email, purpose=purpose, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise ValidationError("Invalid or expired code.")
    if otp.is_expired or otp.has_exceeded_attempts:
        otp.invalidate()
        raise ValidationError("Invalid or expired code.")
    if not otp.matches_code(normalized_code):
        otp.register_failed_attempt()
        raise ValidationError("Invalid or expired code.")
    return otp


def consume_valid_otp(*, email: str, code: str, purpose: str) -> EmailOTP:
    otp = get_valid_otp(email=email, code=code, purpose=purpose)
    otp.mark_verified()
    otp.mark_consumed()
    return otp


def issue_password_reset_verification_token(*, otp: EmailOTP) -> str:
    if otp.purpose != EmailOTP.Purpose.PASSWORD_RESET:
        raise ValidationError("Invalid password reset request.")
    return signing.dumps(
        {
            "otp_id": str(otp.id),
            "email": otp.email,
            "purpose": EmailOTP.Purpose.PASSWORD_RESET,
        },
        salt=PASSWORD_RESET_TOKEN_SALT,
    )


def get_password_reset_otp_from_token(
    *,
    token: str,
    max_age_seconds: int = PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS,
) -> EmailOTP:
    try:
        payload = signing.loads(token, salt=PASSWORD_RESET_TOKEN_SALT, max_age=max_age_seconds)
    except signing.BadSignature as exc:
        raise ValidationError("This password reset session is invalid or has expired.") from exc
    except signing.SignatureExpired as exc:
        raise ValidationError("This password reset session is invalid or has expired.") from exc

    if payload.get("purpose") != EmailOTP.Purpose.PASSWORD_RESET:
        raise ValidationError("This password reset session is invalid or has expired.")

    otp = (
        EmailOTP.objects.select_related("user")
        .filter(
            pk=payload.get("otp_id"),
            email=payload.get("email"),
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            consumed_at__isnull=True,
        )
        .first()
    )
    if not otp or otp.is_expired or otp.verified_at is None:
        raise ValidationError("This password reset session is invalid or has expired.")
    return otp


def complete_signup_verification(*, email: str, code: str) -> User:
    normalized_email = User.objects.normalize_email(email).strip()
    prune_expired_pending_signups(email=normalized_email)
    with transaction.atomic():
        otp = consume_valid_otp(email=normalized_email, code=code, purpose=EmailOTP.Purpose.SIGNUP)
        pending_signup = PendingSignup.objects.filter(email=normalized_email).first()
        company_name = pending_signup.company_name if pending_signup else ""
        company_registration_number = pending_signup.company_registration_number if pending_signup else ""
        subscription_plan_code = pending_signup.subscription_plan_code if pending_signup else ""

        if pending_signup and pending_signup.role == User.Role.ADMIN:
            raise ValidationError(
                "Admin registration requires approval. Please use the admin registration flow to submit your request."
            )

        if otp.user:
            user = otp.user
            if user.role == User.Role.COMPANY:
                ensure_company_profile(
                    user,
                    company_name=company_name,
                    company_registration_number=company_registration_number,
                )
            elif user.role == User.Role.CORPER:
                ensure_corper_profile(user)
            PendingSignup.objects.filter(email=normalized_email).delete()
            return mark_user_email_verified(user, selected_plan_code=subscription_plan_code)

        if not pending_signup:
            raise ValidationError("")
        if deleted_account_email_exists(pending_signup.email):
            raise ValidationError(
                "This email is linked to a previously deleted account. Contact support if you need it restored."
            )
        if User.objects.filter(email=pending_signup.email).exists():
            raise ValidationError("An account with this email already exists.")

        user = User(email=pending_signup.email, role=pending_signup.role)
        user.password = pending_signup.password_hash
        user.save()
        if user.role == User.Role.COMPANY:
            ensure_company_profile(
                user,
                company_name=pending_signup.company_name,
                company_registration_number=pending_signup.company_registration_number,
            )
        elif user.role == User.Role.CORPER:
            ensure_corper_profile(user)
        log_audit_event(
            actor=user,
            action="auth.user_registered",
            target_type="user",
            target_id=str(user.id),
            metadata={"role": user.role},
        )
        pending_signup.delete()
        return mark_user_email_verified(user, selected_plan_code=subscription_plan_code)


def mark_user_email_verified(user: User, *, selected_plan_code: str = ""):
    if user.email_verified:
        return user
    user.email_verified = True
    user.save(update_fields=["email_verified", "updated_at"])
    create_notification(
        recipient=user,
        notification_type=Notification.Type.EMAIL_VERIFICATION_SUCCESS,
        title="Email verified",
        body="Your email address has been verified successfully.",
        data={"user_id": str(user.id)},
    )
    log_audit_event(
        actor=user,
        action="auth.email_verified",
        target_type="user",
        target_id=str(user.id),
        metadata={"verified_at": timezone.now().isoformat()},
    )
    return user
