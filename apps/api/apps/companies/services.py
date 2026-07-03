from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import logging
from smtplib import SMTPException

from apps.accounts.models import User
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import normalize_company_registration_number

logger = logging.getLogger(__name__)


def ensure_company_profile(
    user: User,
    *,
    company_name: str = "",
    company_registration_number: str = "",
) -> CompanyProfile:
    normalized_company_name = company_name.strip()
    normalized_registration_number = normalize_company_registration_number(company_registration_number)
    profile, _ = CompanyProfile.objects.get_or_create(
        user=user,
        defaults={
            "company_name": normalized_company_name,
            "company_registration_number": normalized_registration_number,
            "company_registration_date": None,
            "tax_identification_number": "",
            "company_location_state": "",
            "preferred_deployment_states": "",
            "company_location_city": "",
            "company_address": "",
            "head_office_address": "",
            "company_website": "",
            "company_sector": "",
            "organization_type": "",
            "staff_count_range": "",
            "ppa_capacity": None,
            "office_location_count": None,
            "company_function": "",
            "placement_type": "",
            "monthly_allowance_offered": "",
            "accommodation_provided": "",
            "ppa_support": "",
            "desired_corper_description": "",
            "desired_qualification": "",
            "desired_age_range": "",
            "desired_field_of_study": "",
            "desired_university": "",
            "desired_posting_states": "",
            "desired_skills": "",
            "desired_experience": "",
            "contact_name": "",
            "contact_email": "",
            "contact_phone": "",
            "directors_name": "",
            "director_phone_number": "",
            "legal_acceptances": {},
            "directory_visibility_paused": False,
            "verification_status": CompanyProfile.VerificationStatus.UNSUBMITTED,
        },
    )
    if normalized_company_name and not profile.company_name:
        profile.company_name = normalized_company_name
        profile.updated_at = timezone.now()
        profile.save(update_fields=["company_name", "updated_at"])
    if normalized_registration_number and not profile.company_registration_number:
        profile.company_registration_number = normalized_registration_number
        profile.updated_at = timezone.now()
        profile.save(update_fields=["company_registration_number", "updated_at"])
    return profile


def notify_company_verification_admins(*, company: CompanyProfile) -> None:
    recipient_email = getattr(
        settings,
        "COMPANY_VERIFICATION_ADMIN_EMAIL",
        "admin@corpershub.ng",
    )
    if not recipient_email:
        return

    web_url = getattr(settings, "WEB_URL", "").rstrip("/")
    detail_path = f"/admin/companies/detail?companyId={company.id}"
    detail_url = f"{web_url}{detail_path}" if web_url else detail_path
    subject = f"Company verification pending: {company.company_name or company.user.email}"
    body = (
        "A company profile has been submitted for verification.\n\n"
        f"Company: {company.company_name or 'Not provided'}\n"
        f"Email: {company.user.email}\n"
        f"Registration number: {company.company_registration_number or 'Not provided'}\n"
        f"Tax identification number: {company.tax_identification_number or 'Not provided'}\n"
        f"Review link: {detail_url}\n"
    )
    from_email = getattr(settings, "EMAIL_FROM_EMAIL", "") or settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(subject, body, from_email, [recipient_email], fail_silently=False)
    except (SMTPException, OSError):
        logger.exception(
            "Unable to send company verification email",
            extra={"company_id": str(company.id), "company_email": company.user.email},
        )
