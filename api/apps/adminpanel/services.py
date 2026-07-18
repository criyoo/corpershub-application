from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape
from rest_framework.exceptions import ValidationError

from apps.accounts.tasks import build_web_url
from apps.adminpanel.models import AdminRegistrationRequest
from apps.audit.services import log_audit_event
from apps.accounts.models import PendingSignup, User

logger = logging.getLogger(__name__)


def get_primary_admin_user() -> User | None:
    return User.objects.filter(role=User.Role.ADMIN).order_by("created_at", "id").first()


def validate_admin_registration_password(password: str, *, user: User | None = None) -> str:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc
    return password


def _build_admin_request_email(request: AdminRegistrationRequest) -> tuple[str, str]:
    review_url = build_web_url("/admin/approvals")
    safe_email = escape(request.email)
    safe_review_url = escape(review_url)
    plain_body = (
        f"A new admin access request was submitted for {request.email}.\n\n"
        f"Review the request here: {review_url}\n\n"
        "corpershub Support\n"
        "Email: hello@corpershub.ng\n"
        "Website: https://corpershub.ng"
    )
    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#07140E;padding:0;font-family:Arial,Helvetica,sans-serif;color:#F8FAFC;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#07140E;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;overflow:hidden;border-radius:30px;background:#0B261B;border:1px solid rgba(190,227,202,0.22);">
            <tr>
              <td style="padding:34px 30px;background:linear-gradient(135deg,#134B35 0%,#0B261B 55%,#07140E 100%);">
                <span style="display:inline-block;border-radius:999px;background:rgba(250,204,21,0.16);border:1px solid rgba(250,204,21,0.34);padding:8px 12px;color:#FACC15;font-size:11px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;">Admin approval</span>
                <h1 style="margin:20px 0 0;color:#FFFFFF;font-size:34px;line-height:1.08;font-weight:900;">A new admin access request is waiting</h1>
                <p style="margin:16px 0 0;color:#D6E5DA;font-size:15px;line-height:1.8;">A new corpershub admin registration request was submitted for <strong style="color:#FFFFFF;">{safe_email}</strong>.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:30px;background:#0B261B;">
                <div style="border-radius:26px;background:linear-gradient(135deg,rgba(124,217,161,0.18),rgba(56,189,248,0.14));padding:24px 22px;text-align:left;">
                  <p style="margin:0;color:#06120D;font-size:11px;font-weight:900;letter-spacing:0.18em;text-transform:uppercase;">Review queue</p>
                  <p style="margin:12px 0 0;color:#06120D;font-size:24px;line-height:1.3;font-weight:900;">Approve or reject this request from the admin dashboard</p>
                  <p style="margin:12px 0 0;color:#214233;font-size:14px;line-height:1.7;">Open the admin access queue to verify the requester email and decide whether the account should be activated.</p>
                </div>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto 0;">
                  <tr>
                    <td style="border-radius:999px;background:#BEE3CA;">
                      <a href="{safe_review_url}" style="display:inline-block;padding:15px 24px;color:#06120D;text-decoration:none;font-size:14px;font-weight:900;">Review admin requests</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:22px 0 0;color:#91A99A;font-size:12px;line-height:1.7;text-align:center;">If the button does not work, copy this link into your browser:<br><a href="{safe_review_url}" style="color:#BEE3CA;text-decoration:none;">{safe_review_url}</a></p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 30px 30px;background:#06120D;border-top:1px solid rgba(255,255,255,0.08);">
                <p style="margin:0;color:#FFFFFF;font-size:14px;font-weight:800;">corpershub Support</p>
                <p style="margin:8px 0 0;color:#AFC2B5;font-size:12px;line-height:1.7;">Trusted NYSC placement discovery for corpers and companies.<br>Email: <a href="mailto:hello@corpershub.ng" style="color:#BEE3CA;text-decoration:none;">hello@corpershub.ng</a> · Web: <a href="https://corpershub.ng" style="color:#BEE3CA;text-decoration:none;">corpershub.ng</a></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return plain_body, html_body


def _build_admin_approved_email(email: str) -> tuple[str, str]:
    dashboard_url = build_web_url("/admin/overview")
    safe_email = escape(email)
    safe_dashboard_url = escape(dashboard_url)
    plain_body = (
        f"Hello {email},\n\n"
        "Your corpershub admin access request has been approved.\n\n"
        f"Open your admin dashboard: {dashboard_url}\n\n"
        "corpershub Support\n"
        "Email: hello@corpershub.ng\n"
        "Website: https://corpershub.ng"
    )
    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#07140E;padding:0;font-family:Arial,Helvetica,sans-serif;color:#F8FAFC;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#07140E;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;overflow:hidden;border-radius:30px;background:#0B261B;border:1px solid rgba(190,227,202,0.22);">
            <tr>
              <td style="padding:34px 30px;background:linear-gradient(135deg,#134B35 0%,#0B261B 55%,#07140E 100%);">
                <span style="display:inline-block;border-radius:999px;background:rgba(190,227,202,0.16);border:1px solid rgba(190,227,202,0.34);padding:8px 12px;color:#BEE3CA;font-size:11px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;">Access granted</span>
                <h1 style="margin:20px 0 0;color:#FFFFFF;font-size:34px;line-height:1.08;font-weight:900;">Your admin account is ready</h1>
                <p style="margin:16px 0 0;color:#D6E5DA;font-size:15px;line-height:1.8;">Hello <strong style="color:#FFFFFF;">{safe_email}</strong>, your corpershub admin access request has been approved.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:30px;background:#0B261B;">
                <div style="border-radius:26px;background:linear-gradient(135deg,rgba(124,217,161,0.18),rgba(249,115,22,0.14));padding:24px 22px;text-align:left;">
                  <p style="margin:0;color:#06120D;font-size:11px;font-weight:900;letter-spacing:0.18em;text-transform:uppercase;">Next step</p>
                  <p style="margin:12px 0 0;color:#06120D;font-size:24px;line-height:1.3;font-weight:900;">Sign in to your admin dashboard</p>
                  <p style="margin:12px 0 0;color:#214233;font-size:14px;line-height:1.7;">Use the email address and password you submitted during registration to enter the admin workspace.</p>
                </div>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto 0;">
                  <tr>
                    <td style="border-radius:999px;background:#BEE3CA;">
                      <a href="{safe_dashboard_url}" style="display:inline-block;padding:15px 24px;color:#06120D;text-decoration:none;font-size:14px;font-weight:900;">Open admin dashboard</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:22px 0 0;color:#91A99A;font-size:12px;line-height:1.7;text-align:center;">If the button does not work, copy this link into your browser:<br><a href="{safe_dashboard_url}" style="color:#BEE3CA;text-decoration:none;">{safe_dashboard_url}</a></p>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 30px 30px;background:#06120D;border-top:1px solid rgba(255,255,255,0.08);">
                <p style="margin:0;color:#FFFFFF;font-size:14px;font-weight:800;">corpershub Support</p>
                <p style="margin:8px 0 0;color:#AFC2B5;font-size:12px;line-height:1.7;">Trusted NYSC placement discovery for corpers and companies.<br>Email: <a href="mailto:hello@corpershub.ng" style="color:#BEE3CA;text-decoration:none;">hello@corpershub.ng</a> · Web: <a href="https://corpershub.ng" style="color:#BEE3CA;text-decoration:none;">corpershub.ng</a></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return plain_body, html_body


def send_admin_request_notification(*, request: AdminRegistrationRequest, admin_user: User) -> None:
    plain_body, html_body = _build_admin_request_email(request)
    from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    send_mail(
        "New corpershub admin access request",
        plain_body,
        from_email,
        [admin_user.email],
        fail_silently=False,
        html_message=html_body,
    )


def send_admin_approved_email(*, email: str) -> None:
    plain_body, html_body = _build_admin_approved_email(email)
    from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    send_mail(
        "Your corpershub admin access is approved",
        plain_body,
        from_email,
        [email],
        fail_silently=False,
        html_message=html_body,
    )


def submit_admin_registration_request(*, email: str, password: str) -> dict[str, str]:
    normalized_email = User.objects.normalize_email(email).strip()
    validate_admin_registration_password(password)

    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError({"email": ["An account with this email already exists."]})
    if PendingSignup.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError({"email": ["This email already belongs to an unverified account."]})

    existing_request = AdminRegistrationRequest.objects.filter(email__iexact=normalized_email).first()
    if existing_request and existing_request.status == AdminRegistrationRequest.Status.PENDING:
        raise ValidationError({"email": ["An admin access request for this email is already pending approval."]})

    first_admin = get_primary_admin_user()
    if first_admin is None:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalized_email,
                password=password,
                role=User.Role.ADMIN,
                email_verified=True,
                is_active=True,
                is_staff=True,
            )
            log_audit_event(
                actor=user,
                action="auth.first_admin_registered",
                target_type="user",
                target_id=str(user.id),
                metadata={"email": user.email, "bootstrap": True},
            )
        return {
            "status": "created",
            "message": "First admin account created successfully. Sign in to continue.",
        }

    with transaction.atomic():
        request = existing_request or AdminRegistrationRequest(email=normalized_email)
        request.password_hash = make_password(password)
        request.status = AdminRegistrationRequest.Status.PENDING
        request.reviewed_by = None
        request.reviewed_at = None
        request.notification_sent_at = None
        request.approved_user = None
        request.save()
        log_audit_event(
            action="admin.registration_requested",
            target_type="admin_registration_request",
            target_id=str(request.id),
            metadata={"email": request.email},
        )

    try:
        send_admin_request_notification(request=request, admin_user=first_admin)
    except Exception:
        logger.exception(
            "Unable to send admin registration request notification",
            extra={"request_id": str(request.id), "email": request.email, "admin_email": first_admin.email},
        )
    else:
        request.notification_sent_at = timezone.now()
        request.save(update_fields=["notification_sent_at", "updated_at"])

    return {
        "status": "pending",
        "message": "Admin access request submitted successfully. Wait for approval from the primary admin.",
    }


def review_admin_registration_request(
    *,
    request: AdminRegistrationRequest,
    reviewer: User,
    decision: str,
) -> AdminRegistrationRequest:
    if request.status != AdminRegistrationRequest.Status.PENDING:
        raise ValidationError({"status": "This admin access request has already been reviewed."})

    if decision not in {
        AdminRegistrationRequest.Status.APPROVED,
        AdminRegistrationRequest.Status.REJECTED,
    }:
        raise ValidationError({"status": "Choose either approved or rejected."})

    with transaction.atomic():
        approved_user = request.approved_user
        if decision == AdminRegistrationRequest.Status.APPROVED:
            existing_user = User.objects.filter(email__iexact=request.email).first()
            if existing_user and existing_user.role != User.Role.ADMIN:
                raise ValidationError({"email": "A non-admin account already uses this email address."})
            if existing_user and existing_user.role == User.Role.ADMIN:
                approved_user = existing_user
            else:
                approved_user = User(
                    email=request.email,
                    role=User.Role.ADMIN,
                    email_verified=True,
                    is_active=True,
                    is_staff=True,
                )
                approved_user.password = request.password_hash
                approved_user.save()

        request.status = decision
        request.reviewed_by = reviewer
        request.reviewed_at = timezone.now()
        request.approved_user = approved_user if decision == AdminRegistrationRequest.Status.APPROVED else None
        request.save()
        log_audit_event(
            actor=reviewer,
            action="admin.registration_reviewed",
            target_type="admin_registration_request",
            target_id=str(request.id),
            metadata={"decision": decision, "email": request.email},
        )

    if decision == AdminRegistrationRequest.Status.APPROVED:
        try:
            send_admin_approved_email(email=request.email)
        except Exception:
            logger.exception(
                "Unable to send approved admin access email",
                extra={"request_id": str(request.id), "email": request.email},
            )

    return request
