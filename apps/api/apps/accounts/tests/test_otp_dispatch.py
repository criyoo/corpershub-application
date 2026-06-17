import smtplib
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import SimpleTestCase, override_settings

from apps.accounts.services import OTPEmailDeliveryError, dispatch_otp_email
from apps.accounts.tasks import deliver_otp_email, send_otp_email


class OTPDispatchTests(SimpleTestCase):
    @patch("apps.accounts.services.settings", new=SimpleNamespace())
    @patch("apps.accounts.services.send_otp_email_task.delay")
    def test_dispatch_defaults_to_async_queueing_when_setting_is_missing(self, delay_mock):
        dispatch_otp_email(email="corper@example.com", code="A1B2C3", purpose="signup")

        delay_mock.assert_called_once_with("corper@example.com", "A1B2C3", "signup")

    @override_settings(OTP_EMAIL_ASYNC=False)
    @patch("apps.accounts.services.deliver_otp_email")
    @patch("apps.accounts.services.send_otp_email_task.delay")
    def test_dispatch_can_fall_back_to_sync_delivery(self, delay_mock, send_email_mock):
        dispatch_otp_email(email="corper@example.com", code="A1B2C3", purpose="signup")

        send_email_mock.assert_called_once_with("corper@example.com", "A1B2C3", "signup")
        delay_mock.assert_not_called()

    @override_settings(OTP_EMAIL_ASYNC=True)
    @patch("apps.accounts.services.deliver_otp_email")
    @patch("apps.accounts.services.send_otp_email_task.delay")
    def test_dispatch_can_use_celery_when_enabled(self, delay_mock, send_email_mock):
        dispatch_otp_email(email="corper@example.com", code="A1B2C3", purpose="signup")

        delay_mock.assert_called_once_with("corper@example.com", "A1B2C3", "signup")
        send_email_mock.assert_not_called()

    @patch(
        "apps.accounts.services.send_otp_email_task.delay",
        side_effect=RuntimeError("queue unavailable"),
    )
    def test_dispatch_raises_service_error_when_queueing_fails(self, _delay_mock):
        with patch("apps.accounts.services.logger.exception"):
            with self.assertRaises(OTPEmailDeliveryError):
                dispatch_otp_email(email="corper@example.com", code="A1B2C3", purpose="signup")

    @override_settings(OTP_EMAIL_ASYNC=False)
    @patch("apps.accounts.services.deliver_otp_email")
    def test_dispatch_raises_service_error_when_sync_delivery_fails(self, send_email_mock):
        send_email_mock.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Error: authentication failed")
        with patch("apps.accounts.services.logger.exception"):
            with self.assertRaises(OTPEmailDeliveryError):
                dispatch_otp_email(email="corper@example.com", code="A1B2C3", purpose="signup")

    @override_settings(
        OTP_EMAIL_FALLBACK_ENABLED=True,
        OTP_EMAIL_FALLBACK_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_deliver_otp_email_uses_fallback_backend_after_smtp_error(self):
        def flaky_send(email, code, purpose, *, backend=None):
            if backend is None:
                raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Error: authentication failed")
            return send_otp_email(email, code, purpose, backend=backend)

        with patch("apps.accounts.tasks.send_otp_email", side_effect=flaky_send):
            deliver_otp_email("corper@example.com", "A1B2C3", "signup")

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@corpershub.ng",
        EMAIL_FROM_EMAIL="info@corpershub.ng",
    )
    def test_send_otp_email_uses_transactional_sender_when_configured(self):
        send_otp_email("corper@example.com", "A1B2C3", "signup")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "info@corpershub.ng")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@corpershub.ng",
        EMAIL_FROM_EMAIL="",
    )
    def test_send_otp_email_falls_back_to_default_sender(self):
        send_otp_email("corper@example.com", "A1B2C3", "signup")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, "noreply@corpershub.ng")
