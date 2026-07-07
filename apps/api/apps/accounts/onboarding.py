from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.html import escape
from rest_framework.exceptions import ValidationError

from apps.accounts.tasks import build_web_url
from apps.companies.models import CompanyProfile
from apps.corpers.models import CorperProfile

logger = logging.getLogger(__name__)


def company_ready_for_approval(company: CompanyProfile) -> bool:
    return (
        company.profile_fields_complete
        and company.terms_accepted
        and company.verification_status == CompanyProfile.VerificationStatus.VERIFIED
    )


def corper_ready_for_approval(corper: CorperProfile) -> bool:
    return corper.is_complete and corper.documents_verified


def sync_company_approval_status(company: CompanyProfile) -> None:
    if company_ready_for_approval(company) and company.approval_status != CompanyProfile.ApprovalStatus.APPROVED:
        company.approval_status = CompanyProfile.ApprovalStatus.APPROVED
        company.save(update_fields=["approval_status", "updated_at"])
    elif not company_ready_for_approval(company) and company.approval_status != CompanyProfile.ApprovalStatus.UNSUBMITTED:
        company.approval_status = CompanyProfile.ApprovalStatus.UNSUBMITTED
        company.save(update_fields=["approval_status", "updated_at"])


def sync_corper_approval_status(corper: CorperProfile) -> None:
    if corper_ready_for_approval(corper):
        target_status = (
            CorperProfile.ApprovalStatus.PENDING
            if corper.approval_status
            in {
                CorperProfile.ApprovalStatus.UNSUBMITTED,
                CorperProfile.ApprovalStatus.REJECTED,
            }
            else corper.approval_status
        )
    else:
        target_status = CorperProfile.ApprovalStatus.UNSUBMITTED

    if target_status != corper.approval_status:
        corper.approval_status = target_status
        corper.save(update_fields=["approval_status", "updated_at"])


def ensure_company_can_be_approved(company: CompanyProfile) -> None:
    if not company_ready_for_approval(company):
        raise ValidationError(
            {"approval_status": "Complete company verification, terms acceptance, and profile details first."}
        )


def ensure_corper_can_be_approved(corper: CorperProfile) -> None:
    if not corper_ready_for_approval(corper):
        raise ValidationError(
            {"approval_status": "Complete corper verification, terms acceptance, and profile details first."}
        )


def _build_welcome_email_body(*, role_label: str, display_name: str, dashboard_url: str) -> tuple[str, str]:
    safe_name = escape(display_name)
    safe_dashboard_url = escape(dashboard_url)
    plain_body = (
        f"Hello {display_name},\n\n"
        f"Welcome to corpershub. Your {role_label.lower()} profile has been approved and is now live on the platform.\n\n"
        f"Open your dashboard: {dashboard_url}\n\n"
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
                <span style="display:inline-block;border-radius:999px;background:rgba(190,227,202,0.16);border:1px solid rgba(190,227,202,0.34);padding:8px 12px;color:#BEE3CA;font-size:11px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;">Welcome aboard</span>
                <h1 style="margin:20px 0 0;color:#FFFFFF;font-size:34px;line-height:1.08;font-weight:900;">Your corpershub profile is approved</h1>
                <p style="margin:16px 0 0;color:#D6E5DA;font-size:15px;line-height:1.8;">Hello <strong style="color:#FFFFFF;">{safe_name}</strong>, your {escape(role_label.lower())} profile has been verified, approved, and activated on corpershub.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:30px;background:#0B261B;">
                <div style="border-radius:26px;background:linear-gradient(135deg,rgba(124,217,161,0.18),rgba(249,115,22,0.14));padding:24px 22px;text-align:left;">
                  <p style="margin:0;color:#06120D;font-size:11px;font-weight:900;letter-spacing:0.18em;text-transform:uppercase;">Next step</p>
                  <p style="margin:12px 0 0;color:#06120D;font-size:24px;line-height:1.3;font-weight:900;">Start using your dashboard</p>
                  <p style="margin:12px 0 0;color:#214233;font-size:14px;line-height:1.7;">Your account is ready for trusted placement discovery, verified profile visibility, and platform conversations.</p>
                </div>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto 0;">
                  <tr>
                    <td style="border-radius:999px;background:#BEE3CA;">
                      <a href="{safe_dashboard_url}" style="display:inline-block;padding:15px 24px;color:#06120D;text-decoration:none;font-size:14px;font-weight:900;">Open dashboard</a>
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


def send_profile_approval_welcome_email(*, email: str, role_label: str, display_name: str, dashboard_path: str) -> None:
    dashboard_url = build_web_url(dashboard_path)
    plain_body, html_body = _build_welcome_email_body(
        role_label=role_label,
        display_name=display_name,
        dashboard_url=dashboard_url,
    )
    from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    send_mail(
        f"Welcome to corpershub, {display_name}",
        plain_body,
        from_email,
        [email],
        fail_silently=False,
        html_message=html_body,
    )


def maybe_send_company_approval_welcome_email(company: CompanyProfile, *, previous_status: str | None = None) -> None:
    if company.approval_status != CompanyProfile.ApprovalStatus.APPROVED:
        return
    if previous_status == CompanyProfile.ApprovalStatus.APPROVED:
        return
    if company.welcome_email_sent_at is not None:
        return

    try:
        send_profile_approval_welcome_email(
            email=company.user.email,
            role_label="Company",
            display_name=company.company_name or company.user.email,
            dashboard_path="/company/corpers",
        )
    except Exception:
        logger.exception(
            "Unable to send company approval welcome email",
            extra={"company_id": str(company.id), "company_email": company.user.email},
        )
        return
    company.welcome_email_sent_at = timezone.now()
    company.save(update_fields=["welcome_email_sent_at", "updated_at"])


def maybe_send_corper_approval_welcome_email(corper: CorperProfile, *, previous_status: str | None = None) -> None:
    if corper.approval_status != CorperProfile.ApprovalStatus.APPROVED:
        return
    if previous_status == CorperProfile.ApprovalStatus.APPROVED:
        return
    if corper.welcome_email_sent_at is not None:
        return

    try:
        send_profile_approval_welcome_email(
            email=corper.user.email,
            role_label="Corper",
            display_name=corper.full_name or corper.user.email,
            dashboard_path="/corper/companies",
        )
    except Exception:
        logger.exception(
            "Unable to send corper approval welcome email",
            extra={"corper_id": str(corper.id), "corper_email": corper.user.email},
        )
        return
    corper.welcome_email_sent_at = timezone.now()
    corper.save(update_fields=["welcome_email_sent_at", "updated_at"])
