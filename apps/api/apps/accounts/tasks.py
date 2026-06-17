import math
from celery import shared_task
from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.utils.html import escape
from smtplib import SMTPAuthenticationError, SMTPException
from urllib.parse import urlencode


OTP_EMAIL_CONFIG = {
    "signup": {
        "subject": "Verify your corpershub email",
        "eyebrow": "Email verification",
        "headline": "Complete your corpershub registration",
        "intro": "Use this verification code to finish creating your account.",
        "plain_label": "verification",
        "cta_label": "Return to email verification",
        "path": "/verify-email",
    },
    "password_reset": {
        "subject": "Reset your corpershub password",
        "eyebrow": "Password reset",
        "headline": "Reset your corpershub password",
        "intro": "Use this password reset code to continue securing your account.",
        "plain_label": "password reset",
        "cta_label": "Return to password reset",
        "path": "/reset-password",
    },
    "company_password_change": {
        "subject": "Confirm your corpershub settings change",
        "eyebrow": "Company settings",
        "headline": "Confirm your password change",
        "intro": "Use this code to confirm the password change requested from your company settings.",
        "plain_label": "company settings",
        "cta_label": "Return to company settings",
        "path": "/company/settings",
    },
    "company_email_change": {
        "subject": "Confirm your corpershub email change",
        "eyebrow": "Company settings",
        "headline": "Confirm your email change",
        "intro": "Use this code to confirm the email change requested from your company settings.",
        "plain_label": "company settings",
        "cta_label": "Return to company settings",
        "path": "/company/settings",
    },
    "company_mobile_change": {
        "subject": "Confirm your corpershub mobile number change",
        "eyebrow": "Company settings",
        "headline": "Confirm your mobile number change",
        "intro": "Use this code to confirm the mobile number change requested from your company settings.",
        "plain_label": "company settings",
        "cta_label": "Return to company settings",
        "path": "/company/settings",
    },
    "company_delete_account": {
        "subject": "Confirm your corpershub account deletion",
        "eyebrow": "Account security",
        "headline": "Confirm account deletion",
        "intro": "Use this code only if you requested to delete your company account.",
        "plain_label": "account deletion",
        "cta_label": "Return to company settings",
        "path": "/company/settings",
    },
}


def get_otp_expiry_minutes() -> int:
    return max(1, math.ceil(int(getattr(settings, "OTP_EXPIRY_SECONDS", 600)) / 60))


def build_web_url(path: str, query: dict[str, str] | None = None) -> str:
    base_url = getattr(settings, "WEB_URL", "http://localhost:3000").rstrip("/")
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def get_otp_email_config(purpose: str) -> dict[str, str]:
    return OTP_EMAIL_CONFIG.get(purpose, OTP_EMAIL_CONFIG["password_reset"])


def build_otp_action_url(*, email: str, purpose: str) -> str:
    config = get_otp_email_config(purpose)
    query = {"email": email} if purpose in {"signup", "password_reset"} else None
    return build_web_url(config["path"], query=query)


def build_otp_plain_body(*, email: str, code: str, purpose: str, action_url: str) -> str:
    config = get_otp_email_config(purpose)
    expiry_minutes = get_otp_expiry_minutes()
    return (
        f"Your corpershub {config['plain_label']} code is {code}.\n\n"
        f"It expires in {expiry_minutes} minutes. Do not share this code with anyone.\n\n"
        f"Return to corpershub: {action_url}\n\n"
        "corpershub Support\n"
        "Email: hello@corpershub.ng\n"
        "Website: https://corpershub.ng"
    )


def build_otp_html_body(*, email: str, code: str, purpose: str, action_url: str) -> str:
    config = get_otp_email_config(purpose)
    expiry_minutes = get_otp_expiry_minutes()
    logo_url = build_web_url("/images/corpershub-logo.jpeg")
    safe_code = escape(code)
    safe_email = escape(email)
    safe_action_url = escape(action_url)

    return f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#07140E;padding:0;font-family:Arial,Helvetica,sans-serif;color:#F8FAFC;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#07140E;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;overflow:hidden;border-radius:28px;background:#0B261B;border:1px solid rgba(190,227,202,0.20);">
            <tr>
              <td style="padding:0;background:#134B35;">
                <div style="padding:30px 28px;background:linear-gradient(135deg,#134B35 0%,#0B261B 58%,#07140E 100%);">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="vertical-align:middle;">
                        <img src="{logo_url}" alt="corpershub" width="58" height="58" style="display:block;border-radius:999px;border:1px solid rgba(255,255,255,0.25);object-fit:cover;">
                      </td>
                      <td align="right" style="vertical-align:middle;">
                        <span style="display:inline-block;border-radius:999px;background:rgba(190,227,202,0.16);border:1px solid rgba(190,227,202,0.35);padding:8px 12px;color:#BEE3CA;font-size:11px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;">{escape(config["eyebrow"])}</span>
                      </td>
                    </tr>
                  </table>
                  <h1 style="margin:28px 0 0;color:#FFFFFF;font-size:32px;line-height:1.08;font-weight:800;">{escape(config["headline"])}</h1>
                  <p style="margin:14px 0 0;color:#D6E5DA;font-size:15px;line-height:1.7;">{escape(config["intro"])}</p>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:30px 28px 8px;background:#0B261B;">
                <p style="margin:0;color:#D6E5DA;font-size:14px;line-height:1.7;">This code was requested for <strong style="color:#FFFFFF;">{safe_email}</strong>.</p>
                <div style="margin:24px 0;border-radius:22px;background:#F8FAFC;padding:22px;text-align:center;">
                  <p style="margin:0 0 10px;color:#436B56;font-size:11px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;">Your secure code</p>
                  <div style="color:#0B261B;font-size:40px;line-height:1;font-weight:900;letter-spacing:0.18em;">{safe_code}</div>
                  <p style="margin:12px 0 0;color:#436B56;font-size:12px;">Expires in {expiry_minutes} minutes.</p>
                </div>
                <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 22px;">
                  <tr>
                    <td style="border-radius:999px;background:#BEE3CA;">
                      <a href="{safe_action_url}" style="display:inline-block;padding:14px 22px;color:#06120D;text-decoration:none;font-size:14px;font-weight:800;">{escape(config["cta_label"])}</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:0;color:#91A99A;font-size:12px;line-height:1.7;text-align:center;">If the button does not work, copy and paste this link into your browser:<br><a href="{safe_action_url}" style="color:#BEE3CA;text-decoration:none;">{safe_action_url}</a></p>
              </td>
            </tr>
            <tr>
              <td style="padding:26px 28px 30px;background:#06120D;border-top:1px solid rgba(255,255,255,0.08);">
                <p style="margin:0;color:#FFFFFF;font-size:14px;font-weight:800;">corpershub Support</p>
                <p style="margin:8px 0 0;color:#AFC2B5;font-size:12px;line-height:1.7;">Trusted NYSC placement discovery for corpers and companies.<br>Email: <a href="mailto:hello@corpershub.ng" style="color:#BEE3CA;text-decoration:none;">hello@corpershub.ng</a> · Web: <a href="https://corpershub.ng" style="color:#BEE3CA;text-decoration:none;">corpershub.ng</a></p>
                <p style="margin:18px 0 0;color:#6F8778;font-size:11px;line-height:1.6;">For your security, corpershub will never ask you to share this code by phone, chat, or social media.</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_otp_email(
    email: str,
    code: str,
    purpose: str,
    *,
    backend: str | None = None,
):
    config = get_otp_email_config(purpose)
    subject = config["subject"]
    action_url = build_otp_action_url(email=email, purpose=purpose)
    body = build_otp_plain_body(email=email, code=code, purpose=purpose, action_url=action_url)
    html_body = build_otp_html_body(email=email, code=code, purpose=purpose, action_url=action_url)

    from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    connection = get_connection(backend=backend) if backend else None
    send_mail(
        subject,
        body,
        from_email,
        [email],
        fail_silently=False,
        html_message=html_body,
        connection=connection,
    )


def deliver_otp_email(email: str, code: str, purpose: str):
    try:
        send_otp_email(email, code, purpose)
        return True
    except SMTPAuthenticationError:
        if not getattr(settings, "OTP_EMAIL_FALLBACK_ENABLED", False):
            raise
        fallback_backend = getattr(
            settings,
            "OTP_EMAIL_FALLBACK_BACKEND",
            "django.core.mail.backends.console.EmailBackend",
        )
        send_otp_email(email, code, purpose, backend=fallback_backend)
        return True
    except (SMTPException, OSError):
        if not getattr(settings, "OTP_EMAIL_FALLBACK_ENABLED", False):
            raise
        fallback_backend = getattr(
            settings,
            "OTP_EMAIL_FALLBACK_BACKEND",
            "django.core.mail.backends.console.EmailBackend",
        )
        send_otp_email(email, code, purpose, backend=fallback_backend)
        return True


@shared_task
def send_otp_email_task(email: str, code: str, purpose: str):
    deliver_otp_email(email, code, purpose)
