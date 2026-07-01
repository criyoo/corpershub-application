import hashlib
import hmac
import json
import time
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.account_lifecycle import deactivate_expired_corper_account, issue_reactivation_token
from apps.accounts.models import User
from apps.corpers.services import ensure_corper_profile
from apps.payments.models import FlutterwavePaymentRecord, PaymentTransaction, PaymentWebhookEvent
from apps.payments.services import (
    FlutterwaveGateway,
    PAYMENT_ATTEMPT_EXPIRY_MINUTES,
    create_pending_payment,
    process_webhook,
)
from apps.payments.tasks import expire_stale_payment_attempts_task
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import calculate_subscription_end, ensure_trial_subscription
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


def build_flutterwave_checkout(reference: str) -> dict:
    return {
        "reference": reference,
        "authorization_url": f"https://checkout.flutterwave.com/pay/{reference.lower()}",
    }


def complete_corper_onboarding(user: User) -> None:
    digest = hashlib.sha1(user.email.encode("utf-8")).hexdigest().upper()
    unique_suffix = digest[:8]
    phone_digits = "".join(str(int(character, 16) % 10) for character in digest[8:15])
    profile = ensure_corper_profile(user)
    profile.full_name = "Ada Corpers"
    profile.date_of_birth = date(2000, 1, 1)
    profile.posting_location_state = "Lagos"
    profile.batch = "Batch A"
    profile.stream = "Stream 1"
    profile.field_of_study = "Computer Science"
    profile.degree = "BSc"
    profile.university = "University of Lagos"
    profile.university_matriculation_number = f"MAT{unique_suffix}"
    profile.graduation_year = 2023
    profile.profile_photo = "corpers/profile-photos/test.jpg"
    profile.mobile_number = f"+234803{phone_digits}"
    profile.nysc_callup_number = f"NYSC/2024/{unique_suffix}"
    profile.nysc_state_code = f"LA/24A/{unique_suffix}"
    profile.skill = "Backend Engineering"
    profile.technical_skills = "Python, Django"
    profile.soft_skills = "Communication, Teamwork"
    profile.languages_spoken = "English"
    profile.available_date = date(2024, 1, 1)
    profile.bio = "Ready for service."
    profile.terms_of_agreement_accepted_at = timezone.now()
    profile.terms_of_use_accepted_at = timezone.now()
    profile.biodata_verification_status = profile.SensitiveStatus.VERIFIED
    profile.nin_verification_status = profile.SensitiveStatus.VERIFIED
    profile.nysc_callup_verification_status = profile.SensitiveStatus.VERIFIED
    profile.nysc_state_code_verification_status = profile.SensitiveStatus.VERIFIED
    profile.save()


class PaymentFlowTests(APITestCase):
    def setUp(self):
        self.corper_user = User.objects.create_user(
            email="billing-corper@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(self.corper_user)
        self.trial_subscription = ensure_trial_subscription(user=self.corper_user)
        self.paid_plan = SubscriptionPlan.objects.get(code=six)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-FLUTTERWAVETEST123"),
    )
    def test_successful_paid_payment_activates_six_month_subscription_and_expires_trial(self, _mock_initialize):
        with patch.object(
            FlutterwaveGateway,
            "query_payment_status",
            return_value={
                "status": "success",
                "message": "Charge fetched",
                "data": {
                    "id": "chg_12345",
                    "reference": "",
                    "status": "succeeded",
                    "amount": 3500,
                    "currency": "NGN",
                },
            },
        ) as mock_query_status:
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status",
            )

            mock_query_status.return_value["data"]["reference"] = transaction.reference
            mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
            mock_query_status.return_value["data"]["currency"] = transaction.currency
            payload = {
                "type": "charge.completed",
                "data": {
                    "id": "chg_12345",
                    "reference": transaction.reference,
                    "status": "succeeded",
                },
            }
            process_webhook(
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                raw_body=json.dumps(payload).encode("utf-8"),
                signature=hmac.new(
                    b"webhook-secret-hash", json.dumps(payload).encode("utf-8"), digestmod=hashlib.sha256
                ).hexdigest(),
            )

        transaction.refresh_from_db()
        paid_subscription = UserSubscription.objects.get(pk=transaction.subscription_id)
        self.trial_subscription.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESSFUL)
        self.assertEqual(paid_subscription.status, UserSubscription.Status.ACTIVE)
        self.assertEqual(
            paid_subscription.ends_at,
            calculate_subscription_end(plan=self.paid_plan, starts_at=paid_subscription.starts_at),
        )
        self.assertEqual(self.trial_subscription.status, UserSubscription.Status.EXPIRED)

    def test_reactivation_payment_endpoint_rejects_free_plan_for_expired_corper(self):
        corper_user = User.objects.create_user(
            email="expired-corper@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(corper_user)
        ensure_trial_subscription(user=corper_user)
        created_at = timezone.now() - timedelta(days=400)
        User.objects.filter(pk=corper_user.pk).update(created_at=created_at, updated_at=created_at)
        corper_user.refresh_from_db()
        deactivate_expired_corper_account(user=corper_user)
        token = issue_reactivation_token(user=corper_user)

        response = self.client.post(
            "/api/payments/transactions/reactivation/initiate/",
            {
                "token": token,
                "plan_code": "free",
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("free trial is not available", str(response.data["detail"]).lower())

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-REACTPENDING123"),
    )
    def test_reactivation_payment_endpoint_returns_conflict_when_pending_attempt_exists(self, _mock_initialize):
        corper_user = User.objects.create_user(
            email="expired-pending@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(corper_user)
        ensure_trial_subscription(user=corper_user)
        created_at = timezone.now() - timedelta(days=400)
        User.objects.filter(pk=corper_user.pk).update(created_at=created_at, updated_at=created_at)
        corper_user.refresh_from_db()
        deactivate_expired_corper_account(user=corper_user)
        paid_plan = SubscriptionPlan.objects.get(code=six)
        token = issue_reactivation_token(user=corper_user)

        first_response = self.client.post(
            "/api/payments/transactions/reactivation/initiate/",
            {
                "token": token,
                "plan_code": paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        second_response = self.client.post(
            "/api/payments/transactions/reactivation/initiate/",
            {
                "token": token,
                "plan_code": paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 409)
        self.assertIn("pending payment", str(second_response.data["detail"]).lower())
        self.assertEqual(len(second_response.data["pending_attempts"]), 1)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-FLUTTERWAVEREACT123"),
    )
    def test_successful_paid_payment_reactivates_expired_corper(self, _mock_initialize):
        corper_user = User.objects.create_user(
            email="expired-reactivate@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(corper_user)
        ensure_trial_subscription(user=corper_user)
        created_at = timezone.now() - timedelta(days=400)
        User.objects.filter(pk=corper_user.pk).update(created_at=created_at, updated_at=created_at)
        corper_user.refresh_from_db()
        deactivate_expired_corper_account(user=corper_user)
        paid_plan = SubscriptionPlan.objects.get(code=six)
        with patch.object(
            FlutterwaveGateway,
            "query_payment_status",
            return_value={
                "status": "success",
                "message": "Charge fetched",
                "data": {
                    "id": "chg_67890",
                    "reference": "",
                    "status": "succeeded",
                    "amount": 3500,
                    "currency": "NGN",
                },
            },
        ) as mock_query_status:
            transaction, _ = create_pending_payment(
                user=corper_user,
                plan=paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/corper/billing",
            )

            mock_query_status.return_value["data"]["reference"] = transaction.reference
            mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
            mock_query_status.return_value["data"]["currency"] = transaction.currency
            payload = {
                "type": "charge.completed",
                "data": {
                    "id": "chg_67890",
                    "reference": transaction.reference,
                    "status": "succeeded",
                },
            }
            process_webhook(
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                raw_body=json.dumps(payload).encode("utf-8"),
                signature=hmac.new(
                    b"webhook-secret-hash", json.dumps(payload).encode("utf-8"), digestmod=hashlib.sha256
                ).hexdigest(),
            )

        transaction.refresh_from_db()
        corper_user.refresh_from_db()
        paid_subscription = UserSubscription.objects.get(pk=transaction.subscription_id)

        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESSFUL)
        self.assertEqual(paid_subscription.status, UserSubscription.Status.ACTIVE)
        self.assertTrue(corper_user.is_active)
        self.assertEqual(corper_user.deactivation_reason, User.DeactivationReason.NONE)
        self.assertIsNotNone(corper_user.reactivated_at)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-FLUTTERWAVEENDPOINT123"),
    )
    def test_initiate_payment_endpoint_returns_flutterwave_payment_details(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["transaction"]["gateway"], PaymentTransaction.Gateway.FLUTTERWAVE)
        self.assertEqual(
            response.data["checkout"]["authorization_url"],
            "https://checkout.flutterwave.com/pay/cc-flutterwaveendpoint123",
        )
        record = FlutterwavePaymentRecord.objects.get(internal_payment_id=response.data["transaction"]["id"])
        self.assertEqual(record.tx_ref, response.data["transaction"]["reference"])
        self.assertEqual(record.customer_email, self.corper_user.email)
        self.assertEqual(record.status, PaymentTransaction.Status.PENDING)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-FLUTTERWAVEUPGRADE123"),
    )
    def test_active_three_month_plan_can_change_and_new_plan_starts_today(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)
        three_month_plan = SubscriptionPlan.objects.get(code=three)
        six_month_plan = SubscriptionPlan.objects.get(code=six)
        starts_at = timezone.now() - timedelta(days=30)
        ends_at = calculate_subscription_end(plan=three_month_plan, starts_at=starts_at)
        active_subscription = UserSubscription.objects.create(
            user=self.corper_user,
            plan=three_month_plan,
            status=UserSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
        )

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": six_month_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["transaction"]["amount_kobo"], six_month_plan.price_kobo)
        transaction = PaymentTransaction.objects.get(pk=response.data["transaction"]["id"])
        pending_subscription = transaction.subscription
        self.assertIsNotNone(pending_subscription)
        self.assertGreater(pending_subscription.starts_at, starts_at)
        self.assertEqual(
            pending_subscription.metadata["previous_subscription_id"],
            str(active_subscription.id),
        )

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-DOWNGRADE123"),
    )
    def test_active_six_month_plan_cannot_downgrade_to_three_month_plan(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)
        three_month_plan = SubscriptionPlan.objects.get(code=three)
        six_month_plan = SubscriptionPlan.objects.get(code=six)
        starts_at = timezone.now() - timedelta(days=30)
        ends_at = calculate_subscription_end(plan=six_month_plan, starts_at=starts_at)
        UserSubscription.objects.create(
            user=self.corper_user,
            plan=six_month_plan,
            status=UserSubscription.Status.ACTIVE,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=ends_at,
        )

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": three_month_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["transaction"]["amount_kobo"], three_month_plan.price_kobo)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-FLUTTERWAVEEXPIRED123"),
    )
    def test_expired_three_month_plan_can_start_new_plan_at_full_price(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)
        three_month_plan = SubscriptionPlan.objects.get(code=three)
        six_month_plan = SubscriptionPlan.objects.get(code=six)
        starts_at = timezone.now() - timedelta(days=120)
        ends_at = calculate_subscription_end(plan=three_month_plan, starts_at=starts_at)
        UserSubscription.objects.create(
            user=self.corper_user,
            plan=three_month_plan,
            status=UserSubscription.Status.EXPIRED,
            starts_at=starts_at,
            ends_at=ends_at,
            next_billing_at=None,
        )

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": six_month_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["transaction"]["amount_kobo"], six_month_plan.price_kobo)
        transaction = PaymentTransaction.objects.get(pk=response.data["transaction"]["id"])
        pending_subscription = transaction.subscription
        self.assertIsNotNone(pending_subscription)
        self.assertGreater(pending_subscription.starts_at, ends_at)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-PROCESSING123"),
    )
    def test_expire_stale_payment_attempts_task_does_not_expire_processing_attempts(self, _mock_initialize):
        transaction, _ = create_pending_payment(
            user=self.corper_user,
            plan=self.paid_plan,
            gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
            return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
        )
        PaymentTransaction.objects.filter(pk=transaction.pk).update(
            status=PaymentTransaction.Status.PROCESSING,
            created_at=timezone.now() - timedelta(minutes=PAYMENT_ATTEMPT_EXPIRY_MINUTES + 5),
        )

        expired_count = expire_stale_payment_attempts_task()

        transaction.refresh_from_db()
        self.assertEqual(expired_count, 0)
        self.assertEqual(transaction.status, PaymentTransaction.Status.PROCESSING)

    def test_company_cannot_start_subscription_payment(self):
        company_user = User.objects.create_user(
            email="billing@company.ng",
            password="CompanyPass123!",
            role="company",
            email_verified=True,
        )
        self.client.force_authenticate(user=company_user)

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "Only corper accounts can start a subscription.")

    def test_corper_can_start_free_trial_from_billing_once_after_signup(self):
        corper_user = User.objects.create_user(
            email="new-corper@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(corper_user)
        self.client.force_authenticate(user=corper_user)

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": "free",
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "Your 7-day free trial is now active.")
        subscription = UserSubscription.objects.get(user=corper_user)
        self.assertEqual(subscription.status, UserSubscription.Status.TRIAL)
        self.assertEqual(subscription.plan.code, "free")

    def test_corper_cannot_start_free_trial_twice_from_billing(self):
        corper_user = User.objects.create_user(
            email="existing-corper@demo.ng",
            password="CorperPass123!",
            role="corper",
            email_verified=True,
        )
        complete_corper_onboarding(corper_user)
        ensure_trial_subscription(user=corper_user)
        self.client.force_authenticate(user=corper_user)

        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": "free",
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("can only be started once", str(response.data["detail"]).lower())

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-PENDING123"),
    )
    def test_initiate_payment_returns_conflict_when_pending_attempt_exists(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)

        first_response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )
        self.assertEqual(first_response.status_code, 201)

        second_response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertIn("pending payment", str(second_response.data["detail"]).lower())
        self.assertEqual(len(second_response.data["pending_attempts"]), 1)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-CANCEL123"),
    )
    def test_user_can_cancel_pending_payment_attempt(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)
        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )
        transaction_id = response.data["transaction"]["id"]

        cancel_response = self.client.post(
            f"/api/payments/transactions/{transaction_id}/cancel/",
            format="json",
        )

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["status"], PaymentTransaction.Status.CANCELLED)
        transaction = PaymentTransaction.objects.get(pk=transaction_id)
        self.assertEqual(transaction.status, PaymentTransaction.Status.CANCELLED)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-ATTEMPTS123"),
    )
    def test_payment_attempt_list_returns_open_attempts_only(self, _mock_initialize):
        self.client.force_authenticate(user=self.corper_user)
        response = self.client.post(
            "/api/payments/transactions/initiate/",
            {
                "plan_code": self.paid_plan.code,
                "gateway": PaymentTransaction.Gateway.FLUTTERWAVE,
                "callback_url": "https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            },
            format="json",
        )
        transaction = PaymentTransaction.objects.get(pk=response.data["transaction"]["id"])

        attempts_response = self.client.get("/api/payments/transactions/attempts/")

        self.assertEqual(attempts_response.status_code, 200)
        self.assertEqual(attempts_response.data["count"], 1)
        self.assertEqual(attempts_response.data["results"][0]["reference"], transaction.reference)

    @patch.object(
        FlutterwaveGateway,
        "initialize_payment",
        return_value=build_flutterwave_checkout("CC-EXPIRE123"),
    )
    def test_expire_stale_payment_attempts_task_marks_old_pending_attempts_expired(self, _mock_initialize):
        transaction, _ = create_pending_payment(
            user=self.corper_user,
            plan=self.paid_plan,
            gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
            return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
        )
        stale_created_at = timezone.now() - timedelta(minutes=PAYMENT_ATTEMPT_EXPIRY_MINUTES + 1)
        PaymentTransaction.objects.filter(pk=transaction.pk).update(
            created_at=stale_created_at,
            updated_at=stale_created_at,
        )

        expired_count = expire_stale_payment_attempts_task()

        transaction.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(transaction.status, PaymentTransaction.Status.EXPIRED)

    @override_settings(SECRET_KEY="scheduler-secret")
    def test_payment_expiry_trigger_endpoint_rejects_invalid_scheduler_token(self):
        response = self.client.post("/api/payments/internal/expire-stale/", format="json")

        self.assertEqual(response.status_code, 403)

    @override_settings(SECRET_KEY="scheduler-secret")
    @patch("apps.payments.views.expire_stale_payment_attempts_task.delay")
    def test_payment_expiry_trigger_endpoint_queues_celery_task(self, mock_delay):
        token = hashlib.sha256(b"scheduler-secret:payment-expiry-scheduler").hexdigest()

        response = self.client.post(
            "/api/payments/internal/expire-stale/",
            format="json",
            HTTP_X_CORPERSHUB_PAYMENT_EXPIRY_TOKEN=token,
        )

        self.assertEqual(response.status_code, 202)
        mock_delay.assert_called_once_with()

    @override_settings(SECRET_KEY="scheduler-secret")
    @patch("apps.payments.views.expire_stale_payment_attempts_task.delay", side_effect=RuntimeError("broker down"))
    def test_payment_expiry_trigger_endpoint_returns_503_when_queueing_fails(self, _mock_delay):
        token = hashlib.sha256(b"scheduler-secret:payment-expiry-scheduler").hexdigest()

        response = self.client.post(
            "/api/payments/internal/expire-stale/",
            format="json",
            HTTP_X_CORPERSHUB_PAYMENT_EXPIRY_TOKEN=token,
        )

        self.assertEqual(response.status_code, 503)

    @patch.object(
        FlutterwaveGateway,
        "query_payment_status",
        return_value={
            "status": "success",
            "message": "Verification successful",
            "data": {
                "id": "chg_status_123",
                "reference": "",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
            },
        },
    )
    def test_status_endpoint_syncs_pending_flutterwave_payment(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-STATUS123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
                webhook_url="https://example.com/api/payments/webhooks/flutterwave/",
            )

        mock_query_status.return_value["data"]["reference"] = transaction.reference
        mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
        mock_query_status.return_value["data"]["currency"] = transaction.currency
        response = self.client.get(f"/api/payments/transactions/status/?reference={transaction.reference}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], PaymentTransaction.Status.SUCCESSFUL)
        transaction.refresh_from_db()
        self.trial_subscription.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESSFUL)
        self.assertEqual(self.trial_subscription.status, UserSubscription.Status.EXPIRED)

    @patch.object(
        FlutterwaveGateway,
        "query_payment_status",
        return_value={
            "status": "success",
            "message": "Charge fetched",
            "data": {
                "id": "chg_verify_123",
                "reference": "flw_provider_ref_123",
                "tx_ref": "",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
                "customer": {"email": "billing-corper@demo.ng"},
            },
        },
    )
    def test_flutterwave_verify_endpoint_updates_record(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-VERIFY123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            )

        mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
        mock_query_status.return_value["data"]["tx_ref"] = transaction.reference
        response = self.client.get(
            f"/api/payments/transactions/flutterwave/verify/?reference={transaction.reference}&transaction_id=chg_verify_123"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], PaymentTransaction.Status.SUCCESSFUL)
        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(record.flutterwave_transaction_id, "chg_verify_123")
        self.assertEqual(record.status, PaymentTransaction.Status.SUCCESSFUL)
        self.assertIsNotNone(record.verified_at)

    @override_settings(FLUTTERWAVE_SECRET_KEY="test-secret-key")
    @patch("apps.payments.services.urlopen")
    def test_flutterwave_verify_endpoint_uses_v3_api_for_numeric_transaction_id(self, mock_urlopen):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-V3VERIFY123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fcompanies&role=corper",
            )

        verify_response = MagicMock()
        verify_response.read.return_value = json.dumps(
            {
                "status": "success",
                "message": "Transaction fetched successfully",
                "data": {
                    "id": 2052741596,
                    "tx_ref": transaction.reference,
                    "status": "successful",
                    "amount": transaction.amount_kobo / 100,
                    "currency": transaction.currency,
                    "customer": {"email": "billing-corper@demo.ng"},
                },
            }
        ).encode("utf-8")
        verify_context = MagicMock()
        verify_context.__enter__.return_value = verify_response
        mock_urlopen.return_value = verify_context

        response = self.client.get(
            f"/api/payments/transactions/flutterwave/verify/?reference={transaction.reference}"
            f"&transaction_id=2052741596&status=successful"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], PaymentTransaction.Status.SUCCESSFUL)
        request = mock_urlopen.call_args.args[0]
        self.assertIn("/transactions/2052741596/verify", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret-key")

        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(record.flutterwave_transaction_id, "2052741596")
        self.assertEqual(record.status, PaymentTransaction.Status.SUCCESSFUL)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(
        FlutterwaveGateway,
        "query_payment_status",
        return_value={
            "status": "success",
            "message": "Charge fetched",
            "data": {
                "id": "chg_webhook_123",
                "reference": "",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
                "customer": {"email": "billing-corper@demo.ng"},
            },
        },
    )
    def test_flutterwave_webhook_endpoint_processes_signed_events(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-WEBHOOK123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            )

        mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
        mock_query_status.return_value["data"]["reference"] = transaction.reference
        payload = {
            "id": "wbk_api_123",
            "type": "charge.completed",
            "data": {
                "id": "chg_webhook_123",
                "reference": transaction.reference,
                "status": "succeeded",
                "amount": transaction.amount_kobo / 100,
                "currency": transaction.currency,
                "customer": {
                    "email": "billing-corper@demo.ng",
                },
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"webhook-secret-hash", raw_body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/payments/webhooks/flutterwave/",
            data=raw_body,
            content_type="application/json",
            HTTP_FLUTTERWAVE_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESSFUL)
        event = PaymentWebhookEvent.objects.get()
        self.assertEqual(event.event_id, "wbk_api_123")

        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(record.flutterwave_transaction_id, "chg_webhook_123")
        self.assertEqual(record.amount, transaction.amount_kobo / 100)
        self.assertEqual(record.currency, transaction.currency)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    def test_flutterwave_webhook_endpoint_records_failed_event_for_invalid_signature(self):
        payload = {
            "id": "wbk_invalid_sig_123",
            "type": "charge.completed",
            "data": {
                "id": "chg_invalid_sig_123",
                "reference": "CC-INVALIDSIG123",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
            },
        }

        response = self.client.post(
            "/api/payments/webhooks/flutterwave/",
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            HTTP_FLUTTERWAVE_SIGNATURE="invalid-signature",
        )

        self.assertEqual(response.status_code, 400)
        event = PaymentWebhookEvent.objects.get(event_id="wbk_invalid_sig_123")
        self.assertEqual(event.process_status, PaymentWebhookEvent.ProcessStatus.FAILED)
        self.assertEqual(event.signature, "invalid-signature")

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(FlutterwaveGateway, "query_payment_status", side_effect=ValueError("v4 verification unavailable"))
    def test_flutterwave_webhook_records_event_when_verification_fails_for_async_payment_methods(
        self, mock_query_status
    ):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-WEBHOOKBANK123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            )

        payload = {
            "id": "wbk_bank_123",
            "type": "charge.completed",
            "data": {
                "id": "chg_bank_123",
                "reference": transaction.reference,
                "status": "succeeded",
                "amount": transaction.amount_kobo / 100,
                "currency": transaction.currency,
                "customer": {
                    "email": "payer@bank.example",
                },
                "payment_method": {
                    "type": "bank_transfer",
                },
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"webhook-secret-hash", raw_body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/payments/webhooks/flutterwave/",
            data=raw_body,
            content_type="application/json",
            HTTP_FLUTTERWAVE_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.PENDING)
        event = PaymentWebhookEvent.objects.get(event_id="wbk_bank_123")
        self.assertEqual(event.process_status, PaymentWebhookEvent.ProcessStatus.FAILED)
        self.assertEqual(event.payload["data"]["payment_method"]["type"], "bank_transfer")
        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(record.status, PaymentTransaction.Status.PENDING)
        mock_query_status.assert_called()

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(FlutterwaveGateway, "query_payment_status", return_value=None)
    def test_flutterwave_webhook_records_unknown_transaction_events_in_admin(self, mock_query_status):
        payload = {
            "id": "wbk_unknown_reference_123",
            "type": "charge.completed",
            "data": {
                "id": "chg_unknown_reference_123",
                "reference": "CC-UNKNOWNREFERENCE123",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"webhook-secret-hash", raw_body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/payments/webhooks/flutterwave/",
            data=raw_body,
            content_type="application/json",
            HTTP_FLUTTERWAVE_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)
        event = PaymentWebhookEvent.objects.get(event_id="wbk_unknown_reference_123")
        self.assertEqual(event.process_status, PaymentWebhookEvent.ProcessStatus.FAILED)
        self.assertEqual(event.payload["data"]["reference"], "CC-UNKNOWNREFERENCE123")
        mock_query_status.assert_not_called()

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(FlutterwaveGateway, "query_payment_status")
    def test_flutterwave_webhook_processes_later_success_when_same_transaction_gets_multiple_updates(
        self, mock_query_status
    ):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-WEBHOOKPENDING123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            )

        provider_responses = [
            {
                "status": "success",
                "message": "Charge fetched",
                "data": {
                    "id": "chg_webhook_pending_123",
                    "reference": "",
                    "status": "pending",
                    "amount": 3500,
                    "currency": "NGN",
                    "customer": {"email": "billing-corper@demo.ng"},
                },
            },
            {
                "status": "success",
                "message": "Charge fetched",
                "data": {
                    "id": "chg_webhook_pending_123",
                    "reference": "",
                    "status": "succeeded",
                    "amount": 3500,
                    "currency": "NGN",
                    "customer": {"email": "billing-corper@demo.ng"},
                },
            },
        ]
        for response_payload in provider_responses:
            response_payload["data"]["amount"] = transaction.amount_kobo / 100
            response_payload["data"]["reference"] = transaction.reference
        mock_query_status.side_effect = provider_responses

        pending_payload = {
            "type": "charge.completed",
            "data": {
                "id": "chg_webhook_pending_123",
                "reference": transaction.reference,
                "status": "pending",
                "amount": transaction.amount_kobo / 100,
                "currency": "NGN",
                "customer": {
                    "email": "billing-corper@demo.ng",
                },
            },
        }
        success_payload = {
            "type": "charge.completed",
            "data": {
                "id": "chg_webhook_pending_123",
                "reference": transaction.reference,
                "status": "succeeded",
                "amount": transaction.amount_kobo / 100,
                "currency": "NGN",
                "customer": {
                    "email": "billing-corper@demo.ng",
                },
            },
        }

        for payload in (pending_payload, success_payload):
            raw_body = json.dumps(payload).encode("utf-8")
            signature = hmac.new(b"webhook-secret-hash", raw_body, digestmod=hashlib.sha256).hexdigest()
            response = self.client.post(
                "/api/payments/webhooks/flutterwave/",
                data=raw_body,
                content_type="application/json",
                HTTP_FLUTTERWAVE_SIGNATURE=signature,
            )
            self.assertEqual(response.status_code, 200)

        transaction.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESSFUL)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 2)

        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(record.flutterwave_transaction_id, "chg_webhook_pending_123")

    @patch.object(
        FlutterwaveGateway,
        "query_payment_status",
        return_value={
            "status": "success",
            "message": "Charge fetched",
            "data": {
                "id": "chg_redirect_123",
                "reference": "",
                "status": "succeeded",
                "amount": 3500,
                "currency": "NGN",
                "customer": {"email": "billing-corper@demo.ng"},
            },
        },
    )
    def test_flutterwave_redirect_endpoint_redirects_back_to_frontend_status_page(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-REDIRECT123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fcompanies&role=corper",
            )

        mock_query_status.return_value["data"]["amount"] = transaction.amount_kobo / 100
        mock_query_status.return_value["data"]["reference"] = transaction.reference
        response = self.client.get(
            f"/api/payments/transactions/flutterwave/redirect/?tx_ref={transaction.reference}&transaction_id=chg_redirect_123&status=successful"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("https://example.com/billing/status", response["Location"])
        self.assertIn(f"reference={transaction.reference}", response["Location"])
        self.assertIn("transaction_id=chg_redirect_123", response["Location"])

    @patch.object(FlutterwaveGateway, "query_payment_status")
    def test_flutterwave_redirect_endpoint_handles_session_expired_without_provider_lookup(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-REDIRECTEXPIRED123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling&role=corper",
            )

        response = self.client.get(
            f"/api/payments/transactions/flutterwave/redirect/?tx_ref={transaction.reference}&transaction_id=null&status=session_expired"
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("status=expired", response["Location"])
        self.assertNotIn("status=session_expired", response["Location"])
        self.assertNotIn("transaction_id=null", response["Location"])
        mock_query_status.assert_not_called()
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.EXPIRED)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash")
    @patch.object(
        FlutterwaveGateway,
        "query_payment_status",
        return_value={
            "status": "success",
            "message": "Charge fetched",
            "data": {
                "id": "chg_mismatch_123",
                "reference": "",
                "status": "succeeded",
                "amount": 9999,
                "currency": "NGN",
                "customer": {"email": "billing-corper@demo.ng"},
            },
        },
    )
    def test_flutterwave_webhook_fails_verification_when_amount_mismatches(self, mock_query_status):
        with patch.object(
            FlutterwaveGateway,
            "initialize_payment",
            return_value=build_flutterwave_checkout("CC-MISMATCH123"),
        ):
            transaction, _ = create_pending_payment(
                user=self.corper_user,
                plan=self.paid_plan,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                return_url="https://example.com/billing/status?billing_path=%2Fcorper%2Fbilling",
            )

        mock_query_status.return_value["data"]["reference"] = transaction.reference
        payload = {
            "webhook_id": "wbk_123",
            "type": "charge.completed",
            "data": {
                "id": "chg_mismatch_123",
                "reference": transaction.reference,
                "status": "succeeded",
                "amount": 9999,
                "currency": "NGN",
                "customer": {"email": "billing-corper@demo.ng"},
            },
        }
        process_webhook(
            gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
            raw_body=json.dumps(payload).encode("utf-8"),
            signature=hmac.new(
                b"webhook-secret-hash", json.dumps(payload).encode("utf-8"), digestmod=hashlib.sha256
            ).hexdigest(),
        )

        transaction.refresh_from_db()
        record = FlutterwavePaymentRecord.objects.get(internal_payment=transaction)
        self.assertEqual(transaction.status, PaymentTransaction.Status.FAILED)
        self.assertEqual(record.status, PaymentTransaction.Status.FAILED)
        self.assertEqual(record.flutterwave_transaction_id, "chg_mismatch_123")
        self.assertIsNotNone(record.verified_at)

    @override_settings(
        FLUTTERWAVE_SETTLEMENT_BANK_NAME="Access Bank",
        FLUTTERWAVE_SETTLEMENT_ACCOUNT_NUMBER="0123456789",
    )
    def test_admin_can_view_flutterwave_settlement_account(self):
        admin_user = User.objects.create_user(
            email="admin@corpershub.ng",
            password="AdminPass123!",
            role="admin",
            email_verified=True,
        )
        self.client.force_authenticate(user=admin_user)

        response = self.client.get("/api/payments/admin/settlement-account/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["configured"])
        self.assertEqual(response.data["bank_name"], "Access Bank")
        self.assertEqual(response.data["account_number"], "0123456789")
        self.assertEqual(response.data["account_number_masked"], "01******89")

    def test_non_admin_cannot_view_flutterwave_settlement_account(self):
        self.client.force_authenticate(user=self.corper_user)

        response = self.client.get("/api/payments/admin/settlement-account/")

        self.assertEqual(response.status_code, 403)

    @override_settings(
        FLUTTERWAVE_PUBLIC_KEY="public-key",
        FLUTTERWAVE_CLIENT_ID="client-id",
        FLUTTERWAVE_CLIENT_SECRET="client-secret",
        FLUTTERWAVE_ENCRYPTION_KEY="test-encryption-key",
        FLUTTERWAVE_API_BASE_URL="https://developersandbox-api.flutterwave.com",
        WEB_URL="https://dev.corpershub.ng",
    )
    def test_flutterwave_gateway_initializes_inline_checkout_payload(self):
        gateway = FlutterwaveGateway()

        checkout = gateway.initialize_payment(
            reference="CC-HEADERS123",
            amount_kobo=1000000,
            currency="NGN",
            email="billing-corper@demo.ng",
            return_url="https://dev.corpershub.ng/billing/status",
            metadata={
                "plan_code": three,
                "customer_name": "Ada Corpers",
                "customer_phone": "+2348031234567",
                "customer_city": "Lagos",
                "customer_state": "Lagos",
            },
        )

        self.assertEqual(checkout["checkout_mode"], "inline")
        self.assertEqual(checkout["flutterwave"]["client_id"], "public-key")
        self.assertEqual(checkout["flutterwave"]["tx_ref"], "CC-HEADERS123")
        self.assertEqual(checkout["flutterwave"]["payment_options"], "card,banktransfer,ussd")
        self.assertEqual(checkout["flutterwave"]["customer"]["name"], "Ada Corpers")
        self.assertEqual(checkout["flutterwave"]["customer"]["phone_number"], "+2348031234567")
        self.assertEqual(
            checkout["redirect_url"],
            "https://dev.corpershub.ng/billing/status?gateway=flutterwave&reference=CC-HEADERS123",
        )

    @override_settings(
        FLUTTERWAVE_PUBLIC_KEY="",
        FLUTTERWAVE_CLIENT_ID="",
        FLUTTERWAVE_CLIENT_SECRET="client-secret",
        FLUTTERWAVE_ENCRYPTION_KEY="test-encryption-key",
        FLUTTERWAVE_API_BASE_URL="https://developersandbox-api.flutterwave.com",
        WEB_URL="https://dev.corpershub.ng",
    )
    def test_flutterwave_gateway_requires_public_key_for_inline_checkout(self):
        gateway = FlutterwaveGateway()

        with self.assertRaisesMessage(ValueError, "Flutterwave checkout is not configured on the server."):
            gateway.initialize_payment(
                reference="CC-INLINE123",
                amount_kobo=1000000,
                currency="NGN",
                email="billing-corper@demo.ng",
                return_url="https://dev.corpershub.ng/billing/status",
                metadata={
                    "plan_code": three,
                    "customer_name": "Ada Corpers",
                    "customer_phone": "+2348031234567",
                },
            )

    @override_settings(
        FLUTTERWAVE_CLIENT_ID="client-id",
        FLUTTERWAVE_CLIENT_SECRET="client-secret",
        FLUTTERWAVE_ENCRYPTION_KEY="test-encryption-key",
        FLUTTERWAVE_WEBHOOK_SECRET_HASH="webhook-secret-hash",
        FLUTTERWAVE_API_BASE_URL="https://developersandbox-api.flutterwave.com",
        WEB_URL="https://dev.corpershub.ng",
    )
    @patch("apps.payments.services.urlopen")
    def test_flutterwave_gateway_queries_v4_charge_by_reference_and_accepts_signed_webhook(self, mock_urlopen):
        verify_response = MagicMock()
        verify_response.read.return_value = json.dumps(
            {
                "status": "success",
                "message": "Charge fetched",
                "data": [
                    {
                        "id": "chg_verify_123",
                        "reference": "CC-V4VERIFY123",
                        "status": "succeeded",
                        "amount": 3500,
                        "currency": "NGN",
                    }
                ],
            }
        ).encode("utf-8")

        verify_context = MagicMock()
        verify_context.__enter__.return_value = verify_response
        mock_urlopen.return_value = verify_context

        gateway = FlutterwaveGateway()
        gateway._access_token = "test-access-token"
        gateway._access_token_expires_at = time.time() + 300

        payload = gateway.query_payment_status(reference="CC-V4VERIFY123")

        request = mock_urlopen.call_args.args[0]
        raw_body = b'{"event":"charge.completed"}'
        signature = hmac.new(b"webhook-secret-hash", raw_body, digestmod=hashlib.sha256).hexdigest()

        self.assertEqual(
            request.full_url,
            "https://developersandbox-api.flutterwave.com/charges?reference=CC-V4VERIFY123&size=10",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer test-access-token")
        self.assertEqual(payload["data"]["reference"], "CC-V4VERIFY123")
        self.assertTrue(gateway.verify_signature(raw_body=raw_body, signature=signature))
        self.assertFalse(gateway.verify_signature(raw_body=raw_body, signature="invalid-hash"))

    @override_settings(
        FLUTTERWAVE_CLIENT_ID="client-id",
        FLUTTERWAVE_CLIENT_SECRET="client-secret",
        FLUTTERWAVE_ENCRYPTION_KEY="test-encryption-key",
        FLUTTERWAVE_API_BASE_URL="https://developersandbox-api.flutterwave.com",
        WEB_URL="https://dev.corpershub.ng",
    )
    def test_flutterwave_gateway_returns_none_before_payment_exists(self):
        gateway = FlutterwaveGateway()
        gateway._access_token = "test-access-token"
        gateway._access_token_expires_at = time.time() + 300

        with patch.object(
            gateway,
            "_request_json",
            return_value={
                "status": "success",
                "message": "No matching charges yet",
                "data": [],
            },
        ):
            self.assertIsNone(gateway.query_payment_status(reference="CC-V4PENDING123"))
