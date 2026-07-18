import hashlib
import hmac
import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.account_lifecycle import build_reactivation_path
from apps.common.permissions import IsAdminUserRole
from apps.corpers.services import ensure_corper_profile
from apps.payments.models import PaymentTransaction
from apps.payments.serializers import (
    FlutterwaveSettlementAccountSerializer,
    InitiatePaymentSerializer,
    PaymentTransactionStatusSerializer,
    PaymentTransactionSerializer,
    ReactivationPaymentSerializer,
)
from apps.payments.services import (
    build_flutterwave_return_url,
    cancel_payment_attempt,
    create_pending_payment,
    get_public_payment_error,
    get_open_payment_attempts,
    normalize_provider_transaction_id,
    process_webhook,
    sync_transaction_status,
    verify_transaction_by_reference,
)
from apps.payments.tasks import expire_stale_payment_attempts_task

from apps.subscriptions.models import SubscriptionPlan
from apps.subscriptions.services import ensure_trial_subscription, get_corper_plan_transition

logger = logging.getLogger(__name__)
PAYMENT_EXPIRY_TOKEN_HEADER = "x-corpershub-payment-expiry-token"


def _get_payment_expiry_trigger_token() -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:payment-expiry-scheduler".encode("utf-8")).hexdigest()


def _build_payment_webhook_url(request, gateway_key: str) -> str:
    if gateway_key == PaymentTransaction.Gateway.FLUTTERWAVE:
        configured_webhook_url = _get_configured_flutterwave_webhook_url()
        if configured_webhook_url:
            return configured_webhook_url
    return request.build_absolute_uri(reverse("payment-webhook", kwargs={"gateway": gateway_key}))


def _get_configured_flutterwave_webhook_url() -> str:
    webhook_url = settings.FLUTTERWAVE_WEBHOOK_URL.strip()
    if webhook_url:
        return webhook_url

    tunnel_url_file = settings.CLOUDFLARE_TUNNEL_URL_FILE.strip()
    if not tunnel_url_file:
        return ""

    try:
        tunnel_url = Path(tunnel_url_file).read_text(encoding="utf-8").strip()
    except OSError:
        return ""

    if not (tunnel_url.startswith("https://") and tunnel_url.endswith(".trycloudflare.com")):
        return ""

    webhook_path = f"/{settings.FLUTTERWAVE_WEBHOOK_PATH.lstrip('/')}"
    return f"{tunnel_url.rstrip('/')}{webhook_path}"


class InitiatePaymentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        if request.user.role != "corper":
            return Response({"detail": "Only corper accounts can start a subscription."}, status=403)
        corper = ensure_corper_profile(request.user)
        if not corper.onboarding_complete:
            return Response(
                {
                    "detail": (
                        "Complete verification, your corper profile, and the profile terms before opening billing."
                    )
                },
                status=403,
            )
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = get_object_or_404(SubscriptionPlan, code=serializer.validated_data["plan_code"], is_active=True)
        if plan.applies_to not in {request.user.role, "both"} and request.user.role != "admin":
            return Response({"detail": "This plan is not available for your account type."}, status=403)
        if plan.price_kobo == 0:
            if request.user.role != "corper":
                return Response(
                    {"detail": "The 7-day free trial is not available from billing for this account type."},
                    status=400,
                )
            if request.user.subscriptions.exists():
                return Response(
                    {"detail": "The 7-day free trial can only be started once per corper account."},
                    status=400,
                )
            subscription = ensure_trial_subscription(
                user=request.user,
                plan=plan,
                metadata_source="billing-selection",
            )
            return Response(
                {
                    "message": "Your 7-day free trial is now active.",
                    "subscription_started": bool(subscription),
                },
                status=status.HTTP_201_CREATED,
            )
        open_attempts = list(get_open_payment_attempts(user=request.user))
        if open_attempts:
            pending_serializer = PaymentTransactionSerializer(open_attempts, many=True)
            same_plan_attempt = next(
                (attempt for attempt in open_attempts if getattr(attempt.subscription.plan, "code", None) == plan.code),
                None,
            )
            detail = (
                "You have a pending payment for this plan. Continue payment or cancel it before starting again."
                if same_plan_attempt is not None
                else "You already have a pending payment for another plan. Continue it, cancel it, or wait for it to expire."
            )
            return Response(
                {
                    "detail": detail,
                    "pending_attempts": pending_serializer.data,
                },
                status=409,
            )
        return_url = serializer.validated_data.get("callback_url") or f"{settings.WEB_URL}/billing/status"
        gateway_key = serializer.validated_data["gateway"]
        webhook_url = _build_payment_webhook_url(request, gateway_key)
        provider_redirect_url = request.build_absolute_uri(reverse("payment-flutterwave-redirect"))
        transition = get_corper_plan_transition(user=request.user, plan=plan)
        try:
            transaction, checkout = create_pending_payment(
                user=request.user,
                plan=plan,
                gateway_key=gateway_key,
                return_url=return_url,
                provider_redirect_url=provider_redirect_url,
                webhook_url=webhook_url,
                amount_kobo=transition.amount_kobo,
                effective_starts_at=transition.effective_starts_at,
                metadata={
                    "is_upgrade": transition.is_upgrade,
                    "previous_subscription_id": (
                        str(transition.previous_subscription.id) if transition.previous_subscription is not None else ""
                    ),
                },
            )
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to start payment right now. Please try again shortly.",
            )
            return Response({"detail": message}, status=response_status)
        return Response(
            {
                "transaction": PaymentTransactionSerializer(transaction).data,
                "checkout": checkout,
            },
            status=status.HTTP_201_CREATED,
        )


class ReactivationPaymentAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ReactivationPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if user.role != "corper":
            return Response({"detail": "Only corper accounts can be reactivated through billing."}, status=403)
        plan = get_object_or_404(SubscriptionPlan, code=serializer.validated_data["plan_code"], is_active=True)
        if plan.applies_to not in {user.role, "both"}:
            return Response({"detail": "This plan is not available for your account type."}, status=403)
        if plan.price_kobo == 0:
            return Response(
                {"detail": "The 7-day free trial is not available when reactivating an expired account."},
                status=400,
            )
        open_attempts = list(get_open_payment_attempts(user=user))
        if open_attempts:
            pending_serializer = PaymentTransactionSerializer(open_attempts, many=True)
            same_plan_attempt = next(
                (attempt for attempt in open_attempts if getattr(attempt.subscription.plan, "code", None) == plan.code),
                None,
            )
            detail = (
                "You have a pending payment for this plan. Continue payment or cancel it before starting again."
                if same_plan_attempt is not None
                else "You already have a pending payment for another plan. Continue it, cancel it, or wait for it to expire."
            )
            return Response(
                {
                    "detail": detail,
                    "pending_attempts": pending_serializer.data,
                },
                status=409,
            )
        gateway_key = serializer.validated_data["gateway"]
        return_url = serializer.validated_data.get("callback_url") or (
            f"{settings.WEB_URL}{build_reactivation_path(token=serializer.validated_data['token'])}"
        )
        webhook_url = _build_payment_webhook_url(request, gateway_key)
        provider_redirect_url = request.build_absolute_uri(reverse("payment-flutterwave-redirect"))
        transition = get_corper_plan_transition(user=user, plan=plan)
        try:
            transaction, checkout = create_pending_payment(
                user=user,
                plan=plan,
                gateway_key=gateway_key,
                return_url=return_url,
                provider_redirect_url=provider_redirect_url,
                webhook_url=webhook_url,
                amount_kobo=transition.amount_kobo,
                effective_starts_at=transition.effective_starts_at,
                metadata={
                    "is_upgrade": transition.is_upgrade,
                    "previous_subscription_id": (
                        str(transition.previous_subscription.id) if transition.previous_subscription is not None else ""
                    ),
                },
            )
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to start payment right now. Please try again shortly.",
            )
            return Response({"detail": message}, status=response_status)
        return Response(
            {
                "transaction": PaymentTransactionSerializer(transaction).data,
                "checkout": checkout,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentTransactionStatusAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        reference = (request.query_params.get("reference") or "").strip()
        if not reference:
            return Response({"detail": "Payment reference is required."}, status=400)

        transaction = get_object_or_404(
            PaymentTransaction.objects.select_related(
                "user",
                "subscription",
                "subscription__plan",
                "flutterwave_record",
            ),
            reference=reference,
        )
        try:
            transaction = sync_transaction_status(transaction=transaction)
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to confirm payment right now. Please try again shortly.",
            )
            return Response({"detail": message}, status=response_status)
        return Response(PaymentTransactionStatusSerializer(transaction).data)


class FlutterwaveTransactionVerifyAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        reference = (request.query_params.get("tx_ref") or request.query_params.get("reference") or "").strip()
        transaction_id = normalize_provider_transaction_id(request.query_params.get("transaction_id"))
        provider_status = (request.query_params.get("status") or "").strip() or None
        if not reference:
            return Response({"detail": "Payment reference is required."}, status=400)
        try:
            transaction = verify_transaction_by_reference(
                reference=reference,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                transaction_id=transaction_id,
                source="verify-endpoint",
                provider_status=provider_status,
            )
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to confirm payment right now. Please try again shortly.",
            )
            return Response({"detail": message}, status=response_status)
        return Response(PaymentTransactionStatusSerializer(transaction).data)


class FlutterwaveRedirectAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        reference = (request.query_params.get("tx_ref") or request.query_params.get("reference") or "").strip()
        transaction_id = normalize_provider_transaction_id(request.query_params.get("transaction_id"))
        provider_status = (request.query_params.get("status") or "").strip() or None
        if not reference:
            return Response({"detail": "Payment reference is required."}, status=400)
        try:
            transaction = verify_transaction_by_reference(
                reference=reference,
                gateway_key=PaymentTransaction.Gateway.FLUTTERWAVE,
                transaction_id=transaction_id,
                source="redirect",
                provider_status=provider_status,
            )
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to confirm payment right now. Please try again shortly.",
            )
            return Response({"detail": message}, status=response_status)
        return HttpResponseRedirect(
            build_flutterwave_return_url(
                transaction=transaction,
                transaction_id=transaction_id,
                status=provider_status,
            )
        )


class PaymentTransactionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        queryset = PaymentTransaction.objects.select_related(
            "user",
            "subscription",
            "subscription__plan",
            "flutterwave_record",
        )
        if self.request.user.role == "admin":
            return queryset
        return queryset.filter(user=self.request.user)


class PaymentAttemptListAPIView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        return get_open_payment_attempts(user=self.request.user)


class CancelPaymentAttemptAPIView(APIView):
    def post(self, request, pk, *args, **kwargs):
        transaction = get_object_or_404(
            PaymentTransaction.objects.select_related(
                "subscription",
                "subscription__plan",
                "flutterwave_record",
            ),
            pk=pk,
            user=request.user,
        )
        transaction = cancel_payment_attempt(transaction=transaction)
        return Response(PaymentTransactionSerializer(transaction).data)


class PaymentTransactionAdminListAPIView(generics.ListAPIView):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAdminUserRole]
    queryset = PaymentTransaction.objects.select_related(
        "user",
        "subscription",
        "subscription__plan",
        "flutterwave_record",
    ).all()
    search_fields = ["reference", "user__email"]
    ordering_fields = ["created_at", "status", "amount_kobo"]


class FlutterwaveSettlementAccountAdminAPIView(APIView):
    permission_classes = [IsAdminUserRole]

    def get(self, request, *args, **kwargs):
        bank_name = settings.FLUTTERWAVE_SETTLEMENT_BANK_NAME.strip()
        account_number = settings.FLUTTERWAVE_SETTLEMENT_ACCOUNT_NUMBER.strip()
        serializer = FlutterwaveSettlementAccountSerializer(
            {
                "provider": PaymentTransaction.Gateway.FLUTTERWAVE,
                "configured": bool(bank_name and account_number),
                "bank_name": bank_name,
                "account_number": account_number,
                "dashboard_configuration_required": True,
            }
        )
        return Response(serializer.data)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, gateway, *args, **kwargs):
        signature = (
            request.headers.get("flutterwave-signature")
            or request.headers.get("verif-hash")
            or request.headers.get("verifi-hash")
            or ""
        )
        logger.info(
            "Received payment webhook.",
            extra={"gateway": gateway, "signature_present": bool(signature)},
        )
        try:
            event = process_webhook(gateway_key=gateway, raw_body=request.body, signature=signature)
        except ValueError as exc:
            message, response_status = get_public_payment_error(
                str(exc),
                default_message="Unable to process the payment update right now.",
            )
            return Response({"detail": message}, status=response_status)
        except Exception:
            logger.exception("Failed to receive payment webhook.", extra={"gateway": gateway})
            return Response({"detail": "Unable to receive the payment update right now."}, status=503)
        return Response({"message": "Webhook received.", "event_id": str(event.id)})


class TriggerStalePaymentExpiryAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        supplied_token = (request.headers.get(PAYMENT_EXPIRY_TOKEN_HEADER) or "").strip()
        if not supplied_token or not hmac.compare_digest(supplied_token, _get_payment_expiry_trigger_token()):
            return Response({"detail": "Forbidden."}, status=403)

        try:
            expire_stale_payment_attempts_task.delay()
        except Exception:
            logger.exception("Failed to enqueue stale payment expiry task.")
            return Response({"detail": "Unable to enqueue scheduled cleanup right now."}, status=503)

        return Response({"message": "Stale payment expiry task queued."}, status=202)
