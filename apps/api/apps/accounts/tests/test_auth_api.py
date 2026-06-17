from copy import deepcopy
from datetime import timedelta
import smtplib
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.accounts.account_lifecycle import REACTIVATION_PROMPT_MESSAGE, issue_reactivation_token
from apps.accounts.models import DeletedAccount, EmailOTP, PendingSignup, User
from apps.accounts.services import get_valid_otp
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import (
    COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
    CompanyRegistrationLookupResult,
    CompanyRegistrationLookupUnavailable,
)
from apps.companies.services import ensure_company_profile
from apps.corpers.models import CorperProfile, hash_sensitive_identifier
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.models import UserSubscription
from apps.subscriptions.services import ensure_trial_subscription
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()
TEST_OTP_CODE = getattr(settings, "OTP_TEST_CODE", "A1B2C3")


class AuthAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def mock_company_lookup(
        self,
        *,
        company_name: str = "Bright Future Logistics",
        company_registration_number: str = "RC 1754689",
        company_status: str = "ACTIVE",
        registration_date: str = "Date of Registration - Feb 9, 2021",
        company_type: str = "company",
        company_address: str = "IGBOGENE SCHOOL ROAD, ,",
        is_active: bool = True,
    ):
        return patch(
            "apps.accounts.serializers.lookup_company_registration_number",
            return_value=CompanyRegistrationLookupResult(
                company_name=company_name,
                company_registration_number=company_registration_number,
                company_address=company_address,
                company_status=company_status,
                registration_date=registration_date,
                company_type=company_type,
                is_active=is_active,
            ),
        )

    def test_company_registration_rejects_other_free_email_provider(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "owner@yahoo.com",
                "password": "ComplexPass123!",
                "role": "company",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Companies must register", str(response.data))

    def test_company_registration_lookup_returns_company_details(self):
        with self.mock_company_lookup(
            company_name="RUTOB LIMITED",
            company_registration_number="RC 1754689",
            company_status="ACTIVE",
            is_active=True,
        ):
            response = self.client.post(
                "/api/auth/company-registration-lookup/",
                {"company_registration_number": "RC 1754689"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Company registration number verified.")
        self.assertEqual(response.data["data"]["company_name"], "RUTOB LIMITED")
        self.assertEqual(response.data["data"]["company_registration_number"], "RC 1754689")
        self.assertTrue(response.data["data"]["is_active"])

    def test_company_registration_lookup_rejects_invalid_format(self):
        response = self.client.post(
            "/api/auth/company-registration-lookup/",
            {"company_registration_number": "XYZ1234"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            COMPANY_REGISTRATION_NUMBER_VALIDATION_MESSAGE,
        )

    def test_company_registration_lookup_rejects_inactive_company(self):
        with patch(
            "apps.accounts.serializers.lookup_company_registration_number",
            side_effect=ValidationError(
                {
                    "company_registration_number": [
                        "This company registration is inactive with CAC. Visit CAC and update the company status before continuing."
                    ]
                }
            ),
        ):
            response = self.client.post(
                "/api/auth/company-registration-lookup/",
                {"company_registration_number": "RC 1754689"},
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["company_registration_number"][0],
            "This company registration is inactive with CAC. Visit CAC and update the company status before continuing.",
        )

    def test_company_registration_lookup_returns_service_unavailable_when_service_fails(self):
        with patch(
            "apps.accounts.serializers.lookup_company_registration_number",
            side_effect=CompanyRegistrationLookupUnavailable(),
        ):
            response = self.client.post(
                "/api/auth/company-registration-lookup/",
                {"company_registration_number": "RC 1754689"},
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Unable to verify the company registration number", str(response.data))

    def test_company_registration_allows_gmail_for_testing(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "owner@gmail.com",
                "password": "ComplexPass123!",
                "role": "company",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(User.objects.filter(email="owner@gmail.com").exists())
        self.assertTrue(
            PendingSignup.objects.filter(
                email="owner@gmail.com",
                role="company",
                company_name="",
                company_registration_number="",
            ).exists()
        )
        self.assertTrue(EmailOTP.objects.filter(email="owner@gmail.com", purpose="signup").exists())

    def test_corper_registration_creates_pending_signup_and_otp_only(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("debug_otp_code", response.data)
        self.assertFalse(User.objects.filter(email="corper@example.ng").exists())
        self.assertTrue(
            PendingSignup.objects.filter(
                email="corper@example.ng",
                role="corper",
                subscription_plan_code="",
            ).exists()
        )
        self.assertTrue(EmailOTP.objects.filter(email="corper@example.ng", purpose="signup").exists())
        otp = EmailOTP.objects.get(email="corper@example.ng", purpose="signup")
        self.assertNotEqual(otp.code_hash, TEST_OTP_CODE)
        self.assertTrue(otp.matches_code(TEST_OTP_CODE))

    def test_corper_registration_does_not_require_subscription_plan_choice(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "noplan@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PendingSignup.objects.filter(email="noplan@example.ng", role="corper").exists())

    def test_registration_replaces_expired_pending_signup_after_seven_days(self):
        pending_signup = PendingSignup.objects.create(
            email="expired@example.ng",
            role="corper",
            password_hash="stale-hash",
        )
        PendingSignup.objects.filter(pk=pending_signup.pk).update(
            created_at=timezone.now() - timedelta(days=8),
            updated_at=timezone.now() - timedelta(days=8),
        )
        EmailOTP.issue_code(email="expired@example.ng", purpose=EmailOTP.Purpose.SIGNUP)

        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "expired@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PendingSignup.objects.filter(email="expired@example.ng").count(), 1)
        self.assertEqual(EmailOTP.objects.filter(email="expired@example.ng", purpose="signup").count(), 1)

    def test_verify_email_rejects_expired_pending_signup_after_seven_days(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "staleverify@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )
        pending_signup = PendingSignup.objects.get(email="staleverify@example.ng")
        otp = EmailOTP.objects.get(email="staleverify@example.ng", purpose="signup")
        stale_time = timezone.now() - timedelta(days=8)
        PendingSignup.objects.filter(pk=pending_signup.pk).update(created_at=stale_time, updated_at=stale_time)
        EmailOTP.objects.filter(pk=otp.pk).update(created_at=stale_time, updated_at=stale_time)

        response = self.client.post(
            "/api/auth/verify-email/",
            {"email": "staleverify@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data[0], "Invalid or expired code.")
        self.assertFalse(PendingSignup.objects.filter(email="staleverify@example.ng").exists())

    def test_resend_otp_does_not_expose_otp_code(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )
        EmailOTP.objects.filter(email="corper@example.ng", purpose="signup").update(
            last_sent_at=timezone.now() - timedelta(minutes=2)
        )

        response = self.client.post(
            "/api/auth/resend-otp/",
            {"email": "corper@example.ng"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "If the account exists, a fresh OTP has been sent.")
        self.assertNotIn("debug_otp_code", response.data)

    def test_resend_otp_is_rate_limited_for_active_code(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "throttle@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        response = self.client.post(
            "/api/auth/resend-otp/",
            {"email": "throttle@example.ng"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Please wait before requesting another code.", str(response.data))

    def test_invalid_otp_attempts_are_counted_and_eventually_invalidate_the_code(self):
        EmailOTP.issue_code(email="attempts@example.ng", purpose=EmailOTP.Purpose.SIGNUP)

        for expected_attempts in range(1, settings.OTP_MAX_ATTEMPTS + 1):
            with self.assertRaises(ValidationError):
                get_valid_otp(
                    email="attempts@example.ng",
                    code="ZZZZZZ",
                    purpose=EmailOTP.Purpose.SIGNUP,
                )

            otp = EmailOTP.objects.get(email="attempts@example.ng", purpose=EmailOTP.Purpose.SIGNUP)
            self.assertEqual(otp.attempt_count, expected_attempts)

        otp.refresh_from_db()
        self.assertIsNotNone(otp.consumed_at)

        with self.assertRaises(ValidationError):
            get_valid_otp(
                email="attempts@example.ng",
                code=TEST_OTP_CODE,
                purpose=EmailOTP.Purpose.SIGNUP,
            )

    def test_verify_password_reset_code_returns_reset_token(self):
        user = User.objects.create_user(
            email="resetme@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        otp = EmailOTP.issue_code(
            email=user.email,
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            user=user,
        )

        response = self.client.post(
            "/api/auth/reset-password/verify-code/",
            {"email": user.email, "code": TEST_OTP_CODE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Reset code verified.")
        self.assertIn("reset_token", response.data)
        otp.refresh_from_db()
        self.assertIsNotNone(otp.verified_at)
        self.assertIsNone(otp.consumed_at)

    def test_password_reset_verify_uses_separate_throttle_scope_from_code_request(self):
        user = User.objects.create_user(
            email="separate-throttle@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        otp = EmailOTP.issue_code(
            email=user.email,
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            user=user,
        )
        EmailOTP.objects.filter(pk=otp.pk).update(last_sent_at=timezone.now() - timedelta(minutes=2))

        rest_framework_settings = deepcopy(settings.REST_FRAMEWORK)
        rest_framework_settings["DEFAULT_THROTTLE_RATES"] = {
            **rest_framework_settings["DEFAULT_THROTTLE_RATES"],
            "password_reset_request": "1/hour",
            "password_reset_verify": "2/minute",
            "password_reset_complete": "2/minute",
        }

        with override_settings(
            REST_FRAMEWORK=rest_framework_settings,
            OTP_RESEND_WINDOW_SECONDS=0,
        ):
            first_response = self.client.post(
                "/api/auth/forgot-password/",
                {"email": user.email},
                format="json",
            )
            verify_response = self.client.post(
                "/api/auth/reset-password/verify-code/",
                {"email": user.email, "code": TEST_OTP_CODE},
                format="json",
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(verify_response.status_code, 200)
        self.assertIn("reset_token", verify_response.data)

    def test_reset_password_accepts_verified_reset_token(self):
        user = User.objects.create_user(
            email="resetflow@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        otp = EmailOTP.issue_code(
            email=user.email,
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            user=user,
        )
        verify_response = self.client.post(
            "/api/auth/reset-password/verify-code/",
            {"email": user.email, "code": TEST_OTP_CODE},
            format="json",
        )

        response = self.client.post(
            "/api/auth/reset-password/",
            {
                "reset_token": verify_response.data["reset_token"],
                "new_password": "NewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Password reset successful.")
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))
        otp.refresh_from_db()
        self.assertIsNotNone(otp.consumed_at)

    def test_reset_password_still_accepts_email_and_code(self):
        user = User.objects.create_user(
            email="legacyreset@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        otp = EmailOTP.issue_code(
            email=user.email,
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            user=user,
        )

        response = self.client.post(
            "/api/auth/reset-password/",
            {
                "email": user.email,
                "code": TEST_OTP_CODE,
                "new_password": "NewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))

    def test_reset_password_rejects_reusing_existing_password(self):
        user = User.objects.create_user(
            email="reuse-reset@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
        )
        otp = EmailOTP.issue_code(
            email=user.email,
            purpose=EmailOTP.Purpose.PASSWORD_RESET,
            user=user,
        )
        verify_response = self.client.post(
            "/api/auth/reset-password/verify-code/",
            {"email": user.email, "code": TEST_OTP_CODE},
            format="json",
        )

        response = self.client.post(
            "/api/auth/reset-password/",
            {
                "reset_token": verify_response.data["reset_token"],
                "new_password": "OldPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["new_password"][0],
            "New password must be different from your current password.",
        )
        otp.refresh_from_db()
        self.assertIsNone(otp.consumed_at)

    def test_forgot_password_issues_reset_code_for_inactive_existing_user(self):
        user = User.objects.create_user(
            email="inactive-reset@example.com",
            password="OldPass123!",
            role=User.Role.CORPER,
            email_verified=True,
            is_active=False,
        )

        response = self.client.post(
            "/api/auth/forgot-password/",
            {"email": user.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "If the account exists, a reset code has been sent.")
        self.assertTrue(
            EmailOTP.objects.filter(
                email=user.email,
                purpose=EmailOTP.Purpose.PASSWORD_RESET,
                user=user,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_token_refresh_without_body_or_cookie_returns_unauthorized(self):
        response = self.client.post("/api/auth/token/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "No refresh token provided.")

    @patch(
        "apps.accounts.services.send_otp_email_task.delay",
        side_effect=RuntimeError("queue unavailable"),
    )
    def test_corper_registration_returns_service_unavailable_when_otp_queueing_fails(
        self, _send_email_mock
    ):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
                "subscription_plan_code": "free",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Unable to deliver the verification email", str(response.data))

    @override_settings(
        OTP_EMAIL_FALLBACK_ENABLED=True,
        OTP_EMAIL_FALLBACK_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_corper_registration_falls_back_to_configured_backend_when_enabled(self):
        def flaky_send(email, code, purpose, *, backend=None):
            if backend is None:
                raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Error: authentication failed")
            return None

        with patch("apps.accounts.tasks.send_otp_email", side_effect=flaky_send):
            response = self.client.post(
                "/api/auth/register/",
                {
                    "email": "fallback@example.ng",
                    "password": "ComplexPass123!",
                    "role": "corper",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PendingSignup.objects.filter(email="fallback@example.ng").exists())
        self.assertTrue(EmailOTP.objects.filter(email="fallback@example.ng", purpose="signup").exists())

    def test_verify_email_creates_corper_account_and_profile(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="corper@example.ng", purpose="signup")

        response = self.client.post(
            "/api/auth/verify-email/",
            {"email": "corper@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="corper@example.ng")
        self.assertEqual(user.role, "corper")
        self.assertTrue(user.email_verified)
        self.assertTrue(hasattr(user, "corper_profile"))
        self.assertFalse(UserSubscription.objects.filter(user=user).exists())
        self.assertFalse(PendingSignup.objects.filter(email="corper@example.ng").exists())

    def test_verify_email_with_legacy_corper_plan_payload_keeps_signup_without_subscription(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "paidcorper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
                "subscription_plan_code": six,
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="paidcorper@example.ng", purpose="signup")

        response = self.client.post(
            "/api/auth/verify-email/",
            {"email": "paidcorper@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="paidcorper@example.ng")
        self.assertEqual(user.role, "corper")
        self.assertTrue(user.email_verified)
        self.assertFalse(UserSubscription.objects.filter(user=user).exists())

    def test_verify_email_creates_company_account_only_after_otp(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "owner@brightfuture.ng",
                "password": "ComplexPass123!",
                "role": "company",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(User.objects.filter(email="owner@brightfuture.ng").exists())
        otp = EmailOTP.objects.get(email="owner@brightfuture.ng", purpose="signup")

        verify_response = self.client.post(
            "/api/auth/verify-email/",
            {"email": "owner@brightfuture.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        self.assertEqual(verify_response.status_code, 200)
        user = User.objects.get(email="owner@brightfuture.ng")
        self.assertEqual(user.role, "company")
        self.assertTrue(user.email_verified)
        self.assertTrue(hasattr(user, "company_profile"))
        self.assertEqual(user.company_profile.company_name, "")
        self.assertEqual(user.company_profile.company_registration_number, "")
        self.assertFalse(UserSubscription.objects.filter(user=user).exists())
        self.assertEqual(CompanyProfile.objects.get(user=user).company_name, "")
        self.assertEqual(CompanyProfile.objects.get(user=user).company_registration_number, "")
        self.assertFalse(PendingSignup.objects.filter(email="owner@brightfuture.ng").exists())

    def test_login_requires_pending_signup_verification(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Please verify your email before signing in.", str(response.data))

    def test_corper_login_redirects_to_verification_until_documents_are_verified(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="corper@example.ng", purpose="signup")
        self.client.post(
            "/api/auth/verify-email/",
            {"email": "corper@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user"]["profile_completed"])
        self.assertEqual(response.data["user"]["profile_path"], "/corper/verification")
        self.assertTrue(response.data["user"]["needs_subscription_selection"])

    def test_corper_login_redirects_to_profile_after_documents_are_verified(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="corper@example.ng", purpose="signup")
        self.client.post(
            "/api/auth/verify-email/",
            {"email": "corper@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        corper_user = User.objects.get(email="corper@example.ng")
        corper = corper_user.corper_profile
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.save(
            update_fields=[
                "biodata_verification_status",
                "nin_verification_status",
                "nysc_callup_verification_status",
                "nysc_state_code_verification_status",
                "updated_at",
            ]
        )

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "corper@example.ng",
                "password": "ComplexPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user"]["profile_completed"])
        self.assertEqual(response.data["user"]["profile_path"], "/corper/profile")
        self.assertTrue(response.data["user"]["needs_subscription_selection"])

    def test_company_login_keeps_unapproved_company_on_profile_page(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "company@example.ng",
                "password": "ComplexPass123!",
                "role": "company",
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="company@example.ng", purpose="signup")
        self.client.post(
            "/api/auth/verify-email/",
            {"email": "company@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        company_user = User.objects.get(email="company@example.ng")
        company = ensure_company_profile(company_user)
        company.company_name = "Prime Ops Ltd"
        company.company_registration_number = "RC1234567"
        company.tax_identification_number = "TIN1234567"
        company.company_image = "companies/profile-images/company.png"
        company.company_location_state = "Lagos"
        company.preferred_deployment_states = "Lagos, Abuja FCT"
        company.company_location_city = "Ikeja"
        company.company_address = "12 Allen Avenue"
        company.company_sector = "Operations"
        company.company_function = "Logistics"
        company.ppa_capacity = 12
        company.desired_corper_description = "Looking for operations corpers."
        company.desired_qualification = "B.Sc"
        company.desired_age_range = "21-28"
        company.desired_field_of_study = "Business Administration"
        company.desired_university = "University of Lagos"
        company.desired_posting_states = "Lagos"
        company.desired_skills = "Excel, Communication"
        company.desired_experience = "Internship experience"
        company.contact_name = "Grace Prime"
        company.contact_email = "grace@primeops.ng"
        company.contact_phone = "08030000000"
        company.terms_of_agreement_accepted_at = timezone.now()
        company.terms_of_use_accepted_at = timezone.now()
        company.verification_status = CompanyProfile.VerificationStatus.PENDING
        company.save()

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "company@example.ng",
                "password": "ComplexPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["user"]["profile_completed"])
        self.assertEqual(response.data["user"]["profile_path"], "/company/verification")
        self.assertEqual(
            response.data["user"]["company_verification_status"],
            CompanyProfile.VerificationStatus.PENDING,
        )

    def test_company_login_marks_verified_company_as_ready_for_discovery(self):
        self.client.post(
            "/api/auth/register/",
            {
                "email": "verified-company@example.ng",
                "password": "ComplexPass123!",
                "role": "company",
            },
            format="json",
        )
        otp = EmailOTP.objects.get(email="verified-company@example.ng", purpose="signup")
        self.client.post(
            "/api/auth/verify-email/",
            {"email": "verified-company@example.ng", "code": TEST_OTP_CODE},
            format="json",
        )

        company_user = User.objects.get(email="verified-company@example.ng")
        company = ensure_company_profile(company_user)
        company.company_name = "Verified Ops Ltd"
        company.company_registration_number = "RC7654321"
        company.tax_identification_number = "TIN7654321"
        company.company_image = "companies/profile-images/company.png"
        company.company_location_state = "Lagos"
        company.preferred_deployment_states = "Lagos, Abuja FCT"
        company.company_location_city = "Yaba"
        company.company_address = "8 Herbert Macaulay"
        company.company_sector = "Technology"
        company.company_function = "Operations"
        company.ppa_capacity = 12
        company.desired_corper_description = "Looking for verified corpers."
        company.desired_qualification = "B.Sc"
        company.desired_age_range = "21-28"
        company.desired_field_of_study = "Computer Science"
        company.desired_university = "University of Lagos"
        company.desired_posting_states = "Lagos"
        company.desired_skills = "Excel, Reporting"
        company.desired_experience = "Operations support"
        company.contact_name = "Grace Prime"
        company.contact_email = "grace@verifiedops.ng"
        company.contact_phone = "08031111111"
        company.terms_of_agreement_accepted_at = timezone.now()
        company.terms_of_use_accepted_at = timezone.now()
        company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        company.save()

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "verified-company@example.ng",
                "password": "ComplexPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["profile_completed"])
        self.assertEqual(response.data["user"]["profile_path"], "/company/corpers")
        self.assertEqual(
            response.data["user"]["company_verification_status"],
            CompanyProfile.VerificationStatus.VERIFIED,
        )

    def test_expired_corper_login_returns_reactivation_prompt(self):
        user = User.objects.create_user(
            email="expired-corper@example.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        ensure_corper_profile(user)
        ensure_trial_subscription(user=user)
        created_at = timezone.now() - timedelta(days=400)
        User.objects.filter(pk=user.pk).update(created_at=created_at, updated_at=created_at)

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "expired-corper@example.ng",
                "password": "CorperPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(REACTIVATION_PROMPT_MESSAGE, str(response.data))
        self.assertIn("reactivation_required", str(response.data))
        self.assertIn("/corper/billing?reactivation_token=", str(response.data))
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.deactivation_reason, User.DeactivationReason.AUTO_EXPIRED_13_MONTHS)

    def test_reactivation_resolve_returns_corper_billing_path(self):
        user = User.objects.create_user(
            email="expired-resolve@example.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
            is_active=False,
            deactivation_reason=User.DeactivationReason.AUTO_EXPIRED_13_MONTHS,
            deactivated_at=timezone.now(),
        )
        token = issue_reactivation_token(user=user)

        response = self.client.post(
            "/api/auth/reactivation/resolve/",
            {"token": token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], user.email)
        self.assertEqual(response.data["user"]["role"], user.role)
        self.assertTrue(response.data["billing_path"].startswith("/corper/billing?reactivation_token="))

    def test_logout_clears_last_seen_at(self):
        user = User.objects.create_user(
            email="logout@example.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        user.last_seen_at = timezone.now()
        user.save(update_fields=["last_seen_at", "updated_at"])

        self.client.force_authenticate(user)
        response = self.client.post("/api/auth/logout/", format="json")

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertIsNone(user.last_seen_at)


class AccountSettingsAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.corper_user = User.objects.create_user(
            email="corper@example.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        self.company_user = User.objects.create_user(
            email="company@example.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.corper_profile = ensure_corper_profile(self.corper_user)
        self.corper_profile.mobile_number = "08031234567"
        self.corper_profile.save(update_fields=["mobile_number", "updated_at"])
        self.company_profile = ensure_company_profile(self.company_user, company_name="Prime Logistics")
        self.company_profile.contact_phone = "08030000000"
        self.company_profile.save(update_fields=["contact_phone", "updated_at"])

    def test_corper_can_fetch_settings(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.get("/api/auth/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "corper@example.ng")
        self.assertEqual(response.data["mobile_number"], "+2348031234567")
        self.assertEqual(response.data["profile_path"], "/corper/verification")
        self.assertFalse(response.data["profile_visibility_paused"])

    def test_corper_can_pause_profile_visibility(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.patch(
            "/api/auth/settings/profile-visibility/",
            {
                "profile_visibility_paused": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_profile.refresh_from_db()
        self.assertTrue(self.corper_profile.directory_visibility_paused)
        self.assertTrue(response.data["profile_visibility_paused"])

    def test_company_can_pause_profile_visibility(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.patch(
            "/api/auth/settings/profile-visibility/",
            {
                "profile_visibility_paused": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.company_profile.refresh_from_db()
        self.assertTrue(self.company_profile.directory_visibility_paused)
        self.assertTrue(response.data["profile_visibility_paused"])

    def test_change_password_updates_user_password(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-password/",
            {
                "new_password": "UpdatedPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_user.refresh_from_db()
        self.assertTrue(self.corper_user.check_password("UpdatedPass123!"))

    def test_change_email_updates_current_user(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-email/",
            {
                "current_password": "CorperPass123!",
                "new_email": "corper+new@example.ng",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_user.refresh_from_db()
        self.assertEqual(self.corper_user.email, "corper+new@example.ng")
        self.assertEqual(response.data["user"]["email"], "corper+new@example.ng")

    def test_corper_change_mobile_number_updates_corper_profile(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-mobile-number/",
            {
                "current_password": "CorperPass123!",
                "mobile_number": "+2348099990000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_profile.refresh_from_db()
        self.assertEqual(self.corper_profile.mobile_number, "+2348099990000")

    def test_company_change_mobile_number_requires_otp_flow(self):
        self.client.force_authenticate(self.company_user)

        response = self.client.post(
            "/api/auth/settings/change-mobile-number/",
            {
                "current_password": "CompanyPass123!",
                "mobile_number": "08111112222",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("must verify this action with an email OTP", response.data["current_password"][0])

    def test_company_can_change_password_with_otp(self):
        self.client.force_authenticate(self.company_user)

        request_response = self.client.post(
            "/api/auth/settings/company-otp/request/",
            {
                "action": "change_password",
                "new_password": "UpdatedCompanyPass123!",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 200)
        otp = EmailOTP.objects.get(
            email="company@example.ng",
            purpose=EmailOTP.Purpose.COMPANY_PASSWORD_CHANGE,
        )

        confirm_response = self.client.post(
            "/api/auth/settings/company-otp/confirm/",
            {
                "action": "change_password",
                "new_password": "UpdatedCompanyPass123!",
                "otp_code": TEST_OTP_CODE,
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.company_user.refresh_from_db()
        self.assertTrue(self.company_user.check_password("UpdatedCompanyPass123!"))

    def test_company_can_change_email_with_otp(self):
        self.client.force_authenticate(self.company_user)

        request_response = self.client.post(
            "/api/auth/settings/company-otp/request/",
            {
                "action": "change_email",
                "current_password": "CompanyPass123!",
                "new_email": "company+new@example.ng",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 200)
        otp = EmailOTP.objects.get(
            email="company+new@example.ng",
            purpose=EmailOTP.Purpose.COMPANY_EMAIL_CHANGE,
        )

        confirm_response = self.client.post(
            "/api/auth/settings/company-otp/confirm/",
            {
                "action": "change_email",
                "current_password": "CompanyPass123!",
                "new_email": "company+new@example.ng",
                "otp_code": TEST_OTP_CODE,
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_user.email, "company+new@example.ng")

    def test_company_can_change_mobile_number_with_otp(self):
        self.client.force_authenticate(self.company_user)

        request_response = self.client.post(
            "/api/auth/settings/company-otp/request/",
            {
                "action": "change_mobile_number",
                "current_password": "CompanyPass123!",
                "mobile_number": "08111112222",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 200)
        otp = EmailOTP.objects.get(
            email="company@example.ng",
            purpose=EmailOTP.Purpose.COMPANY_MOBILE_CHANGE,
        )

        confirm_response = self.client.post(
            "/api/auth/settings/company-otp/confirm/",
            {
                "action": "change_mobile_number",
                "current_password": "CompanyPass123!",
                "mobile_number": "08111112222",
                "otp_code": TEST_OTP_CODE,
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.company_profile.refresh_from_db()
        self.assertEqual(self.company_profile.contact_phone, "08111112222")

    def test_change_mobile_number_rejects_invalid_prefix(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-mobile-number/",
            {
                "current_password": "CorperPass123!",
                "mobile_number": "+2340000000000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["mobile_number"][0],
            "Enter a valid Nigerian mobile number with a supported network prefix.",
        )

    def test_corper_change_mobile_number_requires_plus_234(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-mobile-number/",
            {
                "current_password": "CorperPass123!",
                "mobile_number": "08099990000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["mobile_number"][0],
            "Enter a valid Nigerian mobile number starting with +234.",
        )

    def test_change_mobile_number_requires_current_password(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/change-mobile-number/",
            {
                "current_password": "WrongPass123!",
                "mobile_number": "+2348099990000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["current_password"][0], "Current password is incorrect.")

    def test_delete_account_archives_user_record(self):
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/auth/settings/delete-account/",
            {"current_password": "CorperPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.corper_user.refresh_from_db()
        self.assertFalse(self.corper_user.is_active)
        self.assertEqual(self.corper_user.deactivation_reason, User.DeactivationReason.ACCOUNT_DELETED)
        self.assertTrue(str(self.corper_user.email).endswith("@deleted.corpershub.local"))
        archived = DeletedAccount.objects.get(original_user_id=self.corper_user.id)
        self.assertEqual(archived.email, "corper@example.ng")

    def test_company_can_delete_account_with_otp(self):
        self.client.force_authenticate(self.company_user)

        request_response = self.client.post(
            "/api/auth/settings/company-otp/request/",
            {
                "action": "delete_account",
                "current_password": "CompanyPass123!",
            },
            format="json",
        )

        self.assertEqual(request_response.status_code, 200)
        otp = EmailOTP.objects.get(
            email="company@example.ng",
            purpose=EmailOTP.Purpose.COMPANY_DELETE_ACCOUNT,
        )

        confirm_response = self.client.post(
            "/api/auth/settings/company-otp/confirm/",
            {
                "action": "delete_account",
                "current_password": "CompanyPass123!",
                "otp_code": TEST_OTP_CODE,
            },
            format="json",
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.company_user.refresh_from_db()
        self.assertFalse(self.company_user.is_active)
        self.assertEqual(self.company_user.deactivation_reason, User.DeactivationReason.ACCOUNT_DELETED)
        archived = DeletedAccount.objects.get(original_user_id=self.company_user.id)
        self.assertEqual(archived.email, "company@example.ng")

    def test_registration_rejects_email_from_deleted_account_archive(self):
        DeletedAccount.objects.create(
            original_user_id=self.company_user.id,
            email="archived@example.ng",
            role=User.Role.CORPER,
        )

        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "archived@example.ng",
                "password": "ComplexPass123!",
                "role": "corper",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("previously deleted account", response.data["email"][0])

    def test_verification_rejects_nin_linked_to_deleted_account(self):
        DeletedAccount.objects.create(
            original_user_id=self.company_user.id,
            email="deleted-corper@example.ng",
            role=User.Role.CORPER,
            nin_lookup_hash=hash_sensitive_identifier("12345678901"),
        )
        self.corper_profile.first_name = "Ada"
        self.corper_profile.surname = "Okafor"
        self.corper_profile.date_of_birth = "1998-06-10"
        self.corper_profile.gender = CorperProfile.Gender.FEMALE
        self.corper_profile.save(
            update_fields=[
                "first_name",
                "surname",
                "date_of_birth",
                "gender",
                "updated_at",
            ]
        )
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": "nin",
                "submitted_value": "12345678901",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("previously deleted account", str(response.data["detail"]).lower())

    def test_verification_rejects_biodata_linked_to_deleted_account(self):
        DeletedAccount.objects.create(
            original_user_id=self.company_user.id,
            email="deleted-biodata@example.ng",
            role=User.Role.CORPER,
            first_name="Ada",
            surname="Okafor",
            date_of_birth="1998-06-10",
        )
        self.client.force_authenticate(self.corper_user)

        response = self.client.post(
            "/api/verification/attempts/",
            {
                "verification_type": "biodata",
                "first_name": "Ada",
                "middle_name": "Grace",
                "surname": "Okafor",
                "date_of_birth": "1998-06-10",
                "gender": "female",
                "mobile_number": "08031234567",
                "university_matriculation_number": "MAT123456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("previously deleted account", str(response.data["detail"]).lower())
