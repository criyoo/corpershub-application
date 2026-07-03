from __future__ import annotations

import calendar
from urllib.parse import quote

from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import log_audit_event

CORPER_ACCOUNT_EXPIRY_MONTHS = 13
REACTIVATION_PROMPT_MESSAGE = "Your account has been deactivated, do you which to reactivate your account?"
REACTIVATION_TOKEN_SALT = "accounts.corper_reactivation"
REACTIVATION_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24


def add_months(value, months: int):
    month_index = value.month - 1 + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def get_corper_account_expiry_at(user: User):
    if user.role != User.Role.CORPER:
        return None
    return add_months(user.created_at, CORPER_ACCOUNT_EXPIRY_MONTHS)


def should_auto_deactivate_corper_account(*, user: User, now=None) -> bool:
    if user.role != User.Role.CORPER or not user.is_active or user.reactivated_at is not None:
        return False
    expires_at = get_corper_account_expiry_at(user)
    if expires_at is None:
        return False
    return (now or timezone.now()) >= expires_at


def deactivate_expired_corper_account(*, user: User, now=None) -> bool:
    if not should_auto_deactivate_corper_account(user=user, now=now):
        return False

    current_time = now or timezone.now()
    user.is_active = False
    user.deactivated_at = current_time
    user.deactivation_reason = User.DeactivationReason.AUTO_EXPIRED_13_MONTHS
    user.save(update_fields=["is_active", "deactivated_at", "deactivation_reason", "updated_at"])
    log_audit_event(
        actor=user,
        action="auth.account_auto_deactivated",
        target_type="user",
        target_id=str(user.id),
        metadata={
            "reason": user.deactivation_reason,
            "deactivated_at": current_time.isoformat(),
        },
    )
    return True


def issue_reactivation_token(*, user: User) -> str:
    if user.role != User.Role.CORPER:
        raise ValidationError("This account cannot be reactivated through billing.")
    return signing.dumps({"user_id": str(user.id), "purpose": "corper-reactivation"}, salt=REACTIVATION_TOKEN_SALT)


def build_reactivation_path(*, token: str) -> str:
    return f"/corper/billing?reactivation_token={quote(token)}"


def get_reactivation_user(*, token: str, max_age_seconds: int = REACTIVATION_TOKEN_MAX_AGE_SECONDS) -> User:
    try:
        payload = signing.loads(token, salt=REACTIVATION_TOKEN_SALT, max_age=max_age_seconds)
    except signing.BadSignature as exc:
        raise ValidationError("This reactivation request is invalid or has expired.") from exc
    except signing.SignatureExpired as exc:
        raise ValidationError("This reactivation request is invalid or has expired.") from exc

    if payload.get("purpose") != "corper-reactivation":
        raise ValidationError("This reactivation request is invalid or has expired.")

    try:
        user = User.objects.get(pk=payload["user_id"])
    except User.DoesNotExist as exc:
        raise ValidationError("This reactivation request is invalid or has expired.") from exc

    deactivate_expired_corper_account(user=user)
    if user.role != User.Role.CORPER:
        raise ValidationError("This account cannot be reactivated through billing.")
    if user.is_active or user.deactivation_reason != User.DeactivationReason.AUTO_EXPIRED_13_MONTHS:
        raise ValidationError("This reactivation request is no longer valid.")
    return user


def reactivate_corper_account(*, user: User, now=None) -> User:
    if user.role != User.Role.CORPER:
        return user

    current_time = now or timezone.now()
    if user.is_active and user.deactivation_reason == User.DeactivationReason.NONE:
        return user

    user.is_active = True
    user.deactivated_at = None
    user.deactivation_reason = User.DeactivationReason.NONE
    user.reactivated_at = current_time
    user.save(
        update_fields=[
            "is_active",
            "deactivated_at",
            "deactivation_reason",
            "reactivated_at",
            "updated_at",
        ]
    )
    log_audit_event(
        actor=user,
        action="auth.account_reactivated",
        target_type="user",
        target_id=str(user.id),
        metadata={"reactivated_at": current_time.isoformat()},
    )
    return user
