from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.account_lifecycle import reactivate_corper_account
from apps.audit.services import log_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.payments.models import FlutterwavePaymentRecord, PaymentTransaction, PaymentWebhookEvent
from apps.subscriptions.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.services import activate_paid_subscription

logger = logging.getLogger(__name__)

PAYMENT_ATTEMPT_EXPIRY_MINUTES = 120
OPEN_PAYMENT_ATTEMPT_STATUSES = (
    PaymentTransaction.Status.PENDING,
    PaymentTransaction.Status.PROCESSING,
)
EXPIRABLE_PAYMENT_ATTEMPT_STATUSES = (
    PaymentTransaction.Status.PENDING,
)
TERMINAL_PAYMENT_STATUSES = (
    PaymentTransaction.Status.SUCCESSFUL,
    PaymentTransaction.Status.FAILED,
    PaymentTransaction.Status.CANCELLED,
    PaymentTransaction.Status.EXPIRED,
    PaymentTransaction.Status.ABANDONED,
)
FAILED_PAYMENT_ATTEMPT_STATUSES = (
    PaymentTransaction.Status.FAILED,
    PaymentTransaction.Status.EXPIRED,
    PaymentTransaction.Status.ABANDONED,
)


class PaymentGateway(ABC):
    gateway_key: str

    @abstractmethod
    def initialize_payment(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        email: str,
        return_url: str,
        webhook_url: str | None = None,
        metadata: dict,
    ):
        raise NotImplementedError

    @abstractmethod
    def verify_signature(self, *, raw_body: bytes, signature: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract_event_id(self, payload: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_reference(self, payload: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_status(self, payload: dict) -> str:
        raise NotImplementedError

    def query_payment_status(self, *, reference: str, transaction_id: str | None = None) -> dict | None:
        raise NotImplementedError


def append_query_params(url: str, **params) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value is not None:
            query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


def encode_json_payload(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def extract_gateway_error_message(body: str, fallback: str) -> str:
    normalized_body = body.strip()
    if not normalized_body:
        return fallback

    try:
        payload = json.loads(normalized_body)
    except json.JSONDecodeError:
        return normalized_body

    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()

        error = payload.get("error")
        if isinstance(error, dict):
            nested_message = error.get("message")
            if isinstance(nested_message, str) and nested_message.strip():
                return nested_message.strip()

    return normalized_body


def is_payment_provider_error(message: str) -> bool:
    normalized = (message or "").strip().lower()
    return any(
        token in normalized
        for token in (
            "flutterwave",
            "authorization key",
            "access token",
            "authentication service",
            "payment services",
            "not configured on the server",
            "invalid response",
            "unable to reach",
        )
    )


def get_public_payment_error(message: str, *, default_message: str) -> tuple[str, int]:
    if is_payment_provider_error(message):
        return default_message, 502
    return message, 400


def get_payment_attempt_expires_at(*, created_at):
    return created_at + timedelta(minutes=PAYMENT_ATTEMPT_EXPIRY_MINUTES)


def normalize_provider_transaction_id(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized or normalized.lower() in {"null", "none", "undefined"}:
        return None
    return normalized


def is_v3_inline_transaction_id(transaction_id: str | None) -> bool:
    normalized = normalize_provider_transaction_id(transaction_id)
    if not normalized:
        return False
    return normalized.isdigit()


def _map_flutterwave_redirect_status(status: str | None) -> str | None:
    normalized = str(status or "").strip().lower()
    if normalized in {"successful", "success", "succeeded", "completed"}:
        return PaymentTransaction.Status.SUCCESSFUL
    if normalized in {"cancelled", "canceled"}:
        return PaymentTransaction.Status.CANCELLED
    if normalized in {"session_expired", "expired"}:
        return PaymentTransaction.Status.EXPIRED
    if normalized in {"abandoned"}:
        return PaymentTransaction.Status.ABANDONED
    if normalized in {"failed", "failure"}:
        return PaymentTransaction.Status.FAILED
    return None


class FlutterwaveGateway(PaymentGateway):
    gateway_key = PaymentTransaction.Gateway.FLUTTERWAVE
    v4_charges_path = "/charges"
    timeout_seconds = 30

    def __init__(self):
        self._access_token = ""
        self._access_token_expires_at = 0.0

    def initialize_payment(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        email: str,
        return_url: str,
        webhook_url: str | None = None,
        metadata: dict,
    ):
        return self._initialize_payment_inline(
            reference=reference,
            amount_kobo=amount_kobo,
            currency=currency,
            email=email,
            return_url=return_url,
            webhook_url=webhook_url,
            metadata=metadata,
        )

    def _initialize_payment_inline(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        email: str,
        return_url: str,
        webhook_url: str | None = None,
        metadata: dict,
    ):
        self._validate_checkout_settings()
        customer_name = str(metadata.get("customer_name") or metadata.get("user_name") or email.split("@", 1)[0]).strip()
        customer_phone = self._format_customer_phone_number(str(metadata.get("customer_phone") or ""))
        redirect_url = str(metadata.get("provider_redirect_url") or "").strip()
        if not redirect_url:
            redirect_url = append_query_params(
                return_url,
                gateway=self.gateway_key,
                reference=reference,
            )
        # Flutterwave inline checkout relies on a dashboard-configured webhook endpoint.
        # The webhook URL can also be passed per-transaction for redundancy.
        flutterwave_checkout = {
            "client_id": self._get_checkout_public_key(),
            "tx_ref": reference,
            "amount": float(self._format_amount(amount_kobo)),
            "currency": currency,
            "payment_options": "card,banktransfer,ussd",
            "redirect_url": redirect_url,
            "webhook_url": webhook_url,
            "customer": {
                "email": email,
                "name": customer_name,
            },
            "customizations": {
                "title": "CorpersHub Subscription",
                "description": str(
                    metadata.get("plan_name") or metadata.get("plan_description") or "CorpersHub subscription"
                ).strip(),
            },
            "meta": {
                "subscription_id": str(metadata.get("subscription_id") or ""),
                "user_id": str(metadata.get("user_id") or ""),
                "plan_code": str(metadata.get("plan_code") or ""),
            },
        }
        if customer_phone:
            flutterwave_checkout["customer"]["phone_number"] = customer_phone

        return {
            "checkout_mode": "inline",
            "redirect_url": redirect_url,
            "flutterwave": flutterwave_checkout,
        }

    def verify_signature(self, *, raw_body: bytes, signature: str) -> bool:
        secret_hash = settings.FLUTTERWAVE_WEBHOOK_SECRET_HASH
        if not secret_hash:
            logger.warning("Flutterwave webhook secret hash not configured.")
            return False
        if not signature:
            return False
        if hmac.compare_digest(secret_hash, signature):
            return True
        expected_base64_signature = base64.b64encode(
            hmac.new(
                secret_hash.encode("utf-8"),
                msg=raw_body,
                digestmod=hashlib.sha256,
            ).digest()
        ).decode("utf-8")
        if hmac.compare_digest(expected_base64_signature, signature):
            return True
        expected_hex_signature = hmac.new(
            secret_hash.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_hex_signature, signature)

    def extract_event_id(self, payload: dict) -> str:
        webhook_id = str(payload.get("id") or payload.get("webhook_id") or "").strip()
        if webhook_id:
            return webhook_id

        transaction_id = str(self._extract_data(payload).get("id") or "").strip()
        if transaction_id:
            dedupe_key = ":".join(
                [
                    str(payload.get("event") or payload.get("type") or "unknown").strip().lower(),
                    self.extract_status(payload),
                    transaction_id,
                ]
            )
            return f"evt_{hashlib.sha256(dedupe_key.encode('utf-8')).hexdigest()}"

        return str(uuid4())

    def extract_reference(self, payload: dict) -> str:
        return _extract_flutterwave_reference(payload)

    def extract_status(self, payload: dict) -> str:
        status_value = str(self._extract_data(payload).get("status", payload.get("status", ""))).lower()
        if status_value in {"success", "successful", "succeeded", "completed"}:
            return "success"
        if status_value in {"pending", "processing", "ongoing", "authorized", "active"}:
            return "processing"
        return "failed"

    def query_payment_status(self, *, reference: str, transaction_id: str | None = None) -> dict | None:
        normalized_transaction_id = normalize_provider_transaction_id(transaction_id)
        if is_v3_inline_transaction_id(normalized_transaction_id):
            v3_payload = self._query_payment_status_v3(
                reference=reference,
                transaction_id=normalized_transaction_id,
            )
            if v3_payload is not None:
                return v3_payload

        try:
            v4_payload = self._query_payment_status_v4(
                reference=reference,
                transaction_id=normalized_transaction_id,
            )
            if v4_payload is not None:
                return v4_payload
        except ValueError:
            if not normalized_transaction_id:
                raise

        return self._query_payment_status_v3(
            reference=reference,
            transaction_id=normalized_transaction_id,
        )

    def _query_payment_status_v3(self, *, reference: str, transaction_id: str | None = None) -> dict | None:
        secret_key = str(getattr(settings, "FLUTTERWAVE_SECRET_KEY", "") or "").strip()
        if not secret_key:
            return None

        v3_base_url = str(getattr(settings, "FLUTTERWAVE_V3_API_BASE_URL", "") or "https://api.flutterwave.com/v3").rstrip(
            "/"
        )
        normalized_transaction_id = normalize_provider_transaction_id(transaction_id)
        if normalized_transaction_id:
            verify_url = f"{v3_base_url}/transactions/{normalized_transaction_id}/verify"
        else:
            verify_url = f"{v3_base_url}/transactions/verify_by_reference?{urlencode({'tx_ref': reference})}"

        request = Request(
            url=verify_url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secret_key}",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = extract_gateway_error_message(body, f"Flutterwave v3 verify failed with HTTP {exc.code}.")
            logger.warning(
                "Flutterwave v3 payment verification failed.",
                extra={"reference": reference, "transaction_id": normalized_transaction_id, "error": message},
            )
            return None
        except URLError as exc:
            logger.warning(
                "Unable to reach Flutterwave v3 verification services.",
                extra={"reference": reference, "transaction_id": normalized_transaction_id, "error": str(exc)},
            )
            return None

        try:
            response_payload = json.loads(raw_response.decode("utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "Flutterwave v3 verification returned an invalid response.",
                extra={"reference": reference, "transaction_id": normalized_transaction_id},
            )
            return None

        if response_payload.get("status") != "success":
            return None

        data = response_payload.get("data") or {}
        if not isinstance(data, dict) or not data:
            return None

        return {
            "status": "success",
            "message": response_payload.get("message"),
            "data": {
                "id": str(data.get("id") or normalized_transaction_id or ""),
                "tx_ref": str(data.get("tx_ref") or reference).strip(),
                "reference": str(data.get("tx_ref") or reference).strip(),
                "status": data.get("status"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "customer": data.get("customer") or {},
            },
        }

    def _query_payment_status_v4(self, *, reference: str, transaction_id: str | None = None) -> dict | None:
        self._validate_settings()
        normalized_transaction_id = normalize_provider_transaction_id(transaction_id)
        if normalized_transaction_id:
            response_payload = self._request_json(
                url=self._build_url(f"{self.v4_charges_path}/{normalized_transaction_id}"),
                method="GET",
            )
        else:
            response_payload = self._request_json(
                url=self._build_url(f"{self.v4_charges_path}?{urlencode({'reference': reference, 'size': 10})}"),
                method="GET",
            )
        if response_payload.get("status") != "success":
            message = response_payload.get("message") or "Unable to verify Flutterwave payment."
            raise ValueError(message)
        data = response_payload.get("data") or []
        if normalized_transaction_id:
            return response_payload
        if isinstance(data, list):
            matching_charge = next(
                (
                    item
                    for item in data
                    if str((item or {}).get("tx_ref") or (item or {}).get("reference") or "").strip() == reference
                ),
                None,
            )
            if matching_charge is None:
                return None
            return {
                "status": response_payload.get("status"),
                "message": response_payload.get("message"),
                "data": matching_charge,
            }
        return response_payload

    def _validate_settings(self) -> None:
        if (
            not settings.FLUTTERWAVE_CLIENT_ID
            or not settings.FLUTTERWAVE_CLIENT_SECRET
            or not settings.FLUTTERWAVE_API_BASE_URL
        ):
            raise ValueError("Flutterwave payments are not configured on the server.")

    def _validate_checkout_settings(self) -> None:
        if not self._get_checkout_public_key():
            raise ValueError("Flutterwave checkout is not configured on the server.")

    def _get_checkout_public_key(self) -> str:
        return str(getattr(settings, "FLUTTERWAVE_PUBLIC_KEY", "") or "").strip()

    def _build_url(self, path: str) -> str:
        return f"{settings.FLUTTERWAVE_API_BASE_URL.rstrip('/')}{path}"

    def _build_headers(self, *, method: str) -> dict[str, str]:
        return self._build_v4_headers(method=method)

    def _build_v4_headers(self, *, method: str) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_access_token()}",
            "User-Agent": f"CorpershubPayments/1.0 ({settings.WEB_URL})",
            "X-Trace-Id": str(uuid4()),
        }
        if method != "GET":
            headers["X-Idempotency-Key"] = uuid4().hex
        return headers

    def _request_access_token(self) -> tuple[str, int]:
        request = Request(
            url=settings.FLUTTERWAVE_TOKEN_URL,
            data=urlencode(
                {
                    "client_id": settings.FLUTTERWAVE_CLIENT_ID,
                    "client_secret": settings.FLUTTERWAVE_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = extract_gateway_error_message(body, f"Flutterwave token request failed with HTTP {exc.code}.")
            raise ValueError(message) from exc
        except URLError as exc:
            raise ValueError("Unable to reach Flutterwave authentication services right now.") from exc

        try:
            response_payload = json.loads(raw_response.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Flutterwave returned an invalid authentication response.") from exc

        access_token = response_payload.get("access_token") or ""
        expires_in = int(response_payload.get("expires_in") or 0)
        if not access_token or expires_in <= 0:
            raise ValueError("Flutterwave did not return a valid access token.")
        return access_token, expires_in

    def _get_access_token(self) -> str:
        current_time = time.time()
        if self._access_token and current_time < self._access_token_expires_at:
            return self._access_token
        access_token, expires_in = self._request_access_token()
        self._access_token = access_token
        self._access_token_expires_at = current_time + max(expires_in - 30, 30)
        return self._access_token

    def _build_customer_payload(self, *, email: str, metadata: dict) -> dict:
        customer_name = str(metadata.get("customer_name") or metadata.get("user_name") or email.split("@", 1)[0]).strip()
        first_name, middle_name, last_name = self._split_name(customer_name)
        country_code, phone_number = self._split_phone_number(str(metadata.get("customer_phone") or ""))
        if not phone_number:
            raise ValueError("Customer phone number is required for Flutterwave payments.")

        city = str(metadata.get("customer_city") or metadata.get("customer_state") or "Lagos").strip() or "Lagos"
        state = str(metadata.get("customer_state") or city).strip() or "Lagos"
        name_payload = {
            "first": first_name,
            "last": last_name,
        }
        normalized_middle_name = middle_name.strip()
        if len(normalized_middle_name) >= 2:
            name_payload["middle"] = normalized_middle_name
        return {
            "address": {
                "country": str(metadata.get("customer_country") or "NG"),
                "city": city,
                "state": state,
                "postal_code": "100001",
                "line1": "CorpersHub",
            },
            "email": email,
            "name": name_payload,
            "phone": {
                "country_code": country_code,
                "number": phone_number,
            },
            "meta": {
                "user_id": metadata.get("user_id") or "",
                "subscription_id": metadata.get("subscription_id") or "",
            },
        }

    def _request_json(self, *, url: str, method: str, payload: dict | None = None) -> dict:
        request = Request(
            url=url,
            data=encode_json_payload(payload) if payload is not None else None,
            headers=self._build_headers(method=method),
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_response = response.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = extract_gateway_error_message(body, f"Flutterwave request failed with HTTP {exc.code}.")
            raise ValueError(message) from exc
        except URLError as exc:
            raise ValueError("Unable to reach Flutterwave payment services right now.") from exc

        try:
            return json.loads(raw_response.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Flutterwave returned an invalid response.") from exc

    def _extract_data(self, payload: dict) -> dict:
        data = payload.get("data") or {}
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    def _format_amount(self, amount_kobo: int) -> float:
        return float(Decimal(amount_kobo) / Decimal("100"))

    def _split_name(self, full_name: str) -> tuple[str, str, str]:
        tokens = [token for token in full_name.split() if token]
        if not tokens:
            return "CorpersHub", "", "User"
        if len(tokens) == 1:
            return tokens[0], "", tokens[0]
        if len(tokens) == 2:
            return tokens[0], "", tokens[1]
        return tokens[0], " ".join(tokens[1:-1]), tokens[-1]

    def _split_phone_number(self, phone_number: str) -> tuple[str, str]:
        digits = "".join(character for character in phone_number if character.isdigit())
        if phone_number.strip().startswith("+") and digits.startswith("234"):
            return "234", digits[3:]
        if digits.startswith("234"):
            return "234", digits[3:]
        if digits.startswith("0"):
            return "234", digits[1:]
        return "234", digits

    def _format_customer_phone_number(self, phone_number: str) -> str:
        country_code, local_number = self._split_phone_number(phone_number)
        if not local_number:
            return ""
        return f"+{country_code}{local_number}"


class CardGateway(PaymentGateway):
    gateway_key = PaymentTransaction.Gateway.CARD

    def initialize_payment(
        self,
        *,
        reference: str,
        amount_kobo: int,
        currency: str,
        email: str,
        return_url: str,
        webhook_url: str | None = None,
        metadata: dict,
    ):
        return {
            "reference": reference,
            "redirect_url": append_query_params(
                return_url,
                gateway=self.gateway_key,
                reference=reference,
            ),
            "provider_redirect_url": metadata.get("provider_redirect_url") or "",
            "amount_kobo": amount_kobo,
            "currency": currency,
            "email": email,
            "metadata": metadata,
        }

    def verify_signature(self, *, raw_body: bytes, signature: str) -> bool:
        return True

    def extract_event_id(self, payload: dict) -> str:
        return str(payload.get("id") or uuid4())

    def extract_reference(self, payload: dict) -> str:
        return payload.get("reference", "")

    def extract_status(self, payload: dict) -> str:
        status_value = payload.get("status", "")
        if status_value == "success":
            return "success"
        if status_value == "failed":
            return "failed"
        return "processing"

    def query_payment_status(self, *, reference: str, transaction_id: str | None = None) -> dict | None:
        raise NotImplementedError


GATEWAYS = {
    PaymentTransaction.Gateway.FLUTTERWAVE: FlutterwaveGateway(),
    PaymentTransaction.Gateway.CARD: CardGateway(),
}


def get_gateway(gateway_key: str) -> PaymentGateway:
    try:
        return GATEWAYS[gateway_key]
    except KeyError as exc:
        raise ValueError("Unsupported payment gateway.") from exc


def create_pending_payment(
    *,
    user,
    plan: SubscriptionPlan,
    gateway_key: str,
    return_url: str,
    provider_redirect_url: str | None = None,
    webhook_url: str | None = None,
    amount_kobo: int | None = None,
    effective_starts_at=None,
    metadata: dict | None = None,
):
    current_time = timezone.now()
    expire_stale_pending_transactions(now=current_time, user=user)
    reference = f"CC-{uuid4().hex[:20].upper()}"
    idempotency_key = uuid4().hex
    amount_to_charge = plan.price_kobo if amount_kobo is None else amount_kobo
    subscription_metadata = {
        "gateway": gateway_key,
        **(metadata or {}),
    }
    if effective_starts_at is not None:
        subscription_metadata["effective_starts_at"] = effective_starts_at.isoformat()

    subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        status=UserSubscription.Status.PENDING,
        starts_at=effective_starts_at or current_time,
        metadata=subscription_metadata,
    )
    transaction = PaymentTransaction.objects.create(
        user=user,
        subscription=subscription,
        gateway=gateway_key,
        reference=reference,
        status=PaymentTransaction.Status.PENDING,
        amount_kobo=amount_to_charge,
        currency=plan.currency,
        idempotency_key=idempotency_key,
        provider_payload={
            "plan_code": plan.code,
            "amount_kobo": amount_to_charge,
            "return_url": return_url,
            "provider_redirect_url": provider_redirect_url or "",
        },
    )
    _sync_flutterwave_record(transaction=transaction, status=transaction.status)
    try:
        checkout = get_gateway(gateway_key).initialize_payment(
            reference=reference,
            amount_kobo=amount_to_charge,
            currency=plan.currency,
            email=user.email,
            return_url=return_url,
            webhook_url=webhook_url,
            metadata={
                "plan_code": plan.code,
                "plan_name": plan.name,
                "plan_description": plan.description,
                "subscription_id": str(subscription.id),
                "user_id": str(user.id),
                "user_name": user.email.split("@", 1)[0],
                "amount_kobo": amount_to_charge,
                "full_plan_price_kobo": plan.price_kobo,
                "provider_redirect_url": provider_redirect_url or "",
                **_build_checkout_customer_metadata(user=user),
            },
        )
    except ValueError as exc:
        logger.warning(
            "Payment initialization failed.",
            extra={
                "gateway": gateway_key,
                "reference": reference,
                "user_id": str(user.id),
                "plan_code": plan.code,
                "error": str(exc),
            },
        )
        transaction.status = PaymentTransaction.Status.FAILED
        transaction.provider_payload = {
            "plan_code": plan.code,
            "amount_kobo": amount_to_charge,
            "return_url": return_url,
            "provider_redirect_url": provider_redirect_url or "",
            "initialization_error": str(exc),
        }
        transaction.save(update_fields=["status", "provider_payload", "updated_at"])
        _sync_flutterwave_record(transaction=transaction, status=transaction.status)
        subscription.status = UserSubscription.Status.PAST_DUE
        subscription.save(update_fields=["status", "updated_at"])
        raise
    transaction.provider_payload = {
        "plan_code": plan.code,
        "amount_kobo": amount_to_charge,
        "return_url": return_url,
        "provider_redirect_url": provider_redirect_url or "",
        "checkout": checkout,
    }
    transaction.save(update_fields=["provider_payload", "updated_at"])
    _sync_flutterwave_record(transaction=transaction, status=transaction.status)
    log_audit_event(
        actor=user,
        action="payment.initiated",
        target_type="payment_transaction",
        target_id=str(transaction.id),
        metadata={
            "gateway": gateway_key,
            "reference": transaction.reference,
            "plan_code": plan.code,
            "amount_kobo": amount_to_charge,
        },
    )
    return transaction, checkout


def _build_checkout_customer_metadata(*, user) -> dict[str, str]:
    default_name = user.email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip() or "CorpersHub User"
    metadata = {
        "customer_name": default_name.title(),
        "customer_phone": "",
        "customer_city": "Lagos",
        "customer_state": "Lagos",
        "customer_country": "NG",
    }

    corper_profile = getattr(user, "corper_profile", None)
    if corper_profile is not None:
        metadata["customer_name"] = (corper_profile.full_name or metadata["customer_name"]).strip()
        metadata["customer_phone"] = (corper_profile.mobile_number or "").strip()
        location_state = (corper_profile.posting_location_state or "").strip()
        if location_state:
            metadata["customer_city"] = location_state
            metadata["customer_state"] = location_state
        return metadata

    company_profile = getattr(user, "company_profile", None)
    if company_profile is not None:
        metadata["customer_name"] = (
            company_profile.contact_name or company_profile.company_name or metadata["customer_name"]
        ).strip()
        metadata["customer_phone"] = (company_profile.contact_phone or "").strip()
        return metadata

    return metadata


def _extract_provider_data(payload: dict | None) -> dict:
    if not payload:
        return {}
    data = payload.get("data")
    if data in (None, {}) and isinstance(payload.get("charge"), dict):
        data = payload["charge"].get("data") or payload["charge"]
    data = data or {}
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


def _extract_nested_mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _extract_flutterwave_reference(payload: dict | None) -> str:
    data = _extract_provider_data(payload)
    meta = _extract_nested_mapping(data.get("meta"))
    top_level_meta = _extract_nested_mapping((payload or {}).get("meta"))

    for container in (data, meta, payload or {}, top_level_meta):
        for key in (
            "tx_ref",
            "txRef",
            "reference",
            "flw_ref",
            "flwRef",
            "customer_reference",
            "customerReference",
        ):
            value = str(container.get(key) or "").strip()
            if value:
                return value
    return ""


def _extract_flutterwave_customer_email(payload: dict | None) -> str:
    data = _extract_provider_data(payload)
    billing_details = _extract_nested_mapping(data.get("billing_details"))
    customer = _extract_nested_mapping(data.get("customer"))

    for container in (billing_details, customer, data):
        value = str(container.get("email") or container.get("customer_email") or "").strip()
        if value:
            return value
    return ""


def _mark_webhook_event_failed(
    *,
    event: PaymentWebhookEvent,
    payload: dict,
    signature: str,
) -> None:
    if event.process_status == PaymentWebhookEvent.ProcessStatus.PROCESSED:
        return
    event.signature = signature or event.signature
    event.payload = payload
    event.process_status = PaymentWebhookEvent.ProcessStatus.FAILED
    event.processed_at = timezone.now()
    event.save(update_fields=["signature", "payload", "process_status", "processed_at", "updated_at"])


def _store_webhook_event(
    *,
    gateway_key: str,
    event_id: str,
    payload: dict,
    signature: str,
) -> PaymentWebhookEvent:
    event, _ = PaymentWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "gateway": gateway_key,
            "event_type": payload.get("event", payload.get("type", "unknown")),
            "signature": signature or "",
            "payload": payload,
        },
    )
    event.gateway = gateway_key
    event.event_type = payload.get("event", payload.get("type", "unknown"))
    event.signature = signature or event.signature
    event.payload = payload
    event.save(update_fields=["gateway", "event_type", "signature", "payload", "updated_at"])
    return event


def _amount_kobo_to_decimal(amount_kobo: int) -> Decimal:
    return (Decimal(amount_kobo) / Decimal("100")).quantize(Decimal("0.01"))


def _normalize_decimal_amount(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _sync_flutterwave_record(
    *,
    transaction: PaymentTransaction,
    payload: dict | None = None,
    status: str | None = None,
    verified: bool = False,
) -> None:
    if transaction.gateway != PaymentTransaction.Gateway.FLUTTERWAVE:
        return

    record, _ = FlutterwavePaymentRecord.objects.get_or_create(
        internal_payment=transaction,
        defaults={
            "tx_ref": transaction.reference,
            "amount": _amount_kobo_to_decimal(transaction.amount_kobo),
            "currency": transaction.currency,
            "customer_email": transaction.user.email,
            "status": transaction.status,
        },
    )

    data = _extract_provider_data(payload)
    customer = data.get("customer") or {}
    billing_details = data.get("billing_details") or {}
    customer_email = (
        str(billing_details.get("email") or customer.get("email") or record.customer_email or transaction.user.email)
        .strip()
    )

    record.tx_ref = transaction.reference
    record.flutterwave_transaction_id = str(
        data.get("id") or record.flutterwave_transaction_id or ""
    ).strip()
    if payload and data.get("amount") is not None:
        record.amount = _normalize_decimal_amount(data.get("amount"))
    if payload and data.get("currency"):
        record.currency = str(data.get("currency")).upper()
    record.customer_email = customer_email or transaction.user.email
    record.status = status or transaction.status
    if verified:
        record.verified_at = timezone.now()
    record.save()


def _transition_subscription_after_unsuccessful_payment(*, transaction: PaymentTransaction, status: str) -> None:
    if transaction.subscription is None:
        return
    if transaction.subscription.status != UserSubscription.Status.PENDING:
        return

    subscription_status = (
        UserSubscription.Status.CANCELLED
        if status == PaymentTransaction.Status.CANCELLED
        else UserSubscription.Status.PAST_DUE
    )
    transaction.subscription.status = subscription_status
    transaction.subscription.save(update_fields=["status", "updated_at"])


def _set_terminal_payment_status(
    *,
    transaction: PaymentTransaction,
    status: str,
    payload: dict | None = None,
    notification_title: str | None = None,
    notification_body: str | None = None,
) -> PaymentTransaction:
    previous_status = transaction.status
    merged_payload = {
        **(transaction.provider_payload if isinstance(transaction.provider_payload, dict) else {}),
        **(payload or {}),
    }
    transaction.status = status
    transaction.provider_payload = merged_payload
    update_fields = ["status", "provider_payload", "updated_at"]
    if status != PaymentTransaction.Status.SUCCESSFUL and transaction.paid_at is not None:
        transaction.paid_at = None
        update_fields.append("paid_at")
    transaction.save(update_fields=update_fields)
    _sync_flutterwave_record(
        transaction=transaction,
        payload=merged_payload,
        status=transaction.status,
        verified=transaction.gateway == PaymentTransaction.Gateway.FLUTTERWAVE,
    )
    _transition_subscription_after_unsuccessful_payment(
        transaction=transaction,
        status=status,
    )
    if notification_title and notification_body:
        create_notification(
            recipient=transaction.user,
            notification_type=(
                Notification.Type.PAYMENT_FAILURE
                if status != PaymentTransaction.Status.SUCCESSFUL
                else Notification.Type.PAYMENT_SUCCESS
            ),
            title=notification_title,
            body=notification_body,
            data={"transaction_id": str(transaction.id)},
        )
    if previous_status != status:
        log_audit_event(
            actor=transaction.user,
            action=f"payment.{status}",
            target_type="payment_transaction",
            target_id=str(transaction.id),
            metadata={
                "reference": transaction.reference,
                "gateway": transaction.gateway,
                "previous_status": previous_status,
            },
        )
    return transaction


def expire_stale_pending_transactions(*, now=None, user=None) -> int:
    current_time = now or timezone.now()
    expiry_cutoff = current_time - timedelta(minutes=PAYMENT_ATTEMPT_EXPIRY_MINUTES)
    queryset = PaymentTransaction.objects.select_related("subscription", "user").filter(
        status__in=EXPIRABLE_PAYMENT_ATTEMPT_STATUSES,
        created_at__lte=expiry_cutoff,
    )
    if user is not None:
        queryset = queryset.filter(user=user)

    expired_count = 0
    for transaction in queryset:
        _set_terminal_payment_status(
            transaction=transaction,
            status=PaymentTransaction.Status.EXPIRED,
            payload={
                "attempt_state": {
                    "expired_at": current_time.isoformat(),
                    "reason": "payment_attempt_timeout",
                }
            },
            notification_title="Payment attempt expired",
            notification_body="Your payment attempt expired before it was completed.",
        )
        expired_count += 1
    return expired_count


def get_open_payment_attempts(*, user):
    expire_stale_pending_transactions(user=user)
    return PaymentTransaction.objects.select_related(
        "subscription",
        "subscription__plan",
        "flutterwave_record",
    ).filter(
        user=user,
        status__in=OPEN_PAYMENT_ATTEMPT_STATUSES,
    )


def cancel_payment_attempt(*, transaction: PaymentTransaction) -> PaymentTransaction:
    if transaction.status not in OPEN_PAYMENT_ATTEMPT_STATUSES:
        return transaction
    return _set_terminal_payment_status(
        transaction=transaction,
        status=PaymentTransaction.Status.CANCELLED,
        payload={
            "attempt_state": {
                "cancelled_at": timezone.now().isoformat(),
                "reason": "cancelled_by_user",
            }
        },
        notification_title="Payment attempt cancelled",
        notification_body="Your pending payment attempt was cancelled.",
    )


def _verify_flutterwave_transaction(
    *,
    transaction: PaymentTransaction,
    transaction_id: str | None = None,
    source: str,
    provider_status: str | None = None,
) -> PaymentTransaction:
    gateway = get_gateway(transaction.gateway)
    existing_record = getattr(transaction, "flutterwave_record", None)
    preferred_transaction_id = (
        normalize_provider_transaction_id(transaction_id)
        or str(getattr(existing_record, "flutterwave_transaction_id", "") or "").strip()
        or None
    )
    redirect_status = _map_flutterwave_redirect_status(provider_status)

    if preferred_transaction_id is None and transaction.status in TERMINAL_PAYMENT_STATUSES:
        _sync_flutterwave_record(transaction=transaction, status=transaction.status)
        return transaction

    if (
        preferred_transaction_id is None
        and redirect_status in {
            PaymentTransaction.Status.CANCELLED,
            PaymentTransaction.Status.EXPIRED,
            PaymentTransaction.Status.ABANDONED,
            PaymentTransaction.Status.FAILED,
        }
    ):
        return _set_terminal_payment_status(
            transaction=transaction,
            status=redirect_status,
            payload={
                "redirect": {
                    "status": str(provider_status or "").strip(),
                    "handled_at": timezone.now().isoformat(),
                }
            },
            notification_title=(
                "Payment attempt cancelled"
                if redirect_status == PaymentTransaction.Status.CANCELLED
                else "Payment attempt expired"
                if redirect_status == PaymentTransaction.Status.EXPIRED
                else "Payment attempt failed"
            ),
            notification_body=(
                "Your payment attempt was cancelled before completion."
                if redirect_status == PaymentTransaction.Status.CANCELLED
                else "Your payment attempt expired before it was completed."
                if redirect_status == PaymentTransaction.Status.EXPIRED
                else "Your payment attempt did not complete successfully."
            ),
        )

    try:
        payload = gateway.query_payment_status(
            reference=transaction.reference,
            transaction_id=preferred_transaction_id,
        )
    except ValueError:
        if not preferred_transaction_id:
            raise
        else:
            payload = gateway.query_payment_status(reference=transaction.reference)

    if payload is None:
        _sync_flutterwave_record(transaction=transaction, status=transaction.status)
        return transaction

    data = _extract_provider_data(payload)
    provider_status = str(data.get("status") or "").strip().lower()
    expected_amount = _amount_kobo_to_decimal(transaction.amount_kobo)
    actual_amount = _normalize_decimal_amount(data.get("amount"))
    expected_currency = transaction.currency.upper()
    actual_currency = str(data.get("currency") or "").upper()
    actual_reference = _extract_flutterwave_reference(payload)
    expected_customer_email = transaction.user.email.strip().lower()
    actual_customer_email = _extract_flutterwave_customer_email(payload).lower()
    verification_errors: list[str] = []
    verification_warnings: list[str] = []

    if actual_reference != transaction.reference:
        verification_errors.append("reference_mismatch")
    if actual_amount != expected_amount:
        verification_errors.append("amount_mismatch")
    if actual_currency != expected_currency:
        verification_errors.append("currency_mismatch")
    if actual_customer_email and actual_customer_email != expected_customer_email:
        verification_warnings.append("customer_email_mismatch")

    existing_payload = transaction.provider_payload if isinstance(transaction.provider_payload, dict) else {}
    verification_payload = {
        **existing_payload,
        "charge": payload,
        "verification": {
            "source": source,
            "reference": actual_reference,
            "transaction_id": str(data.get("id") or preferred_transaction_id or "").strip(),
            "provider_status": provider_status,
            "expected_amount": str(expected_amount),
            "actual_amount": str(actual_amount),
            "expected_currency": expected_currency,
            "actual_currency": actual_currency,
            "expected_customer_email": expected_customer_email,
            "actual_customer_email": actual_customer_email,
            "errors": verification_errors,
            "warnings": verification_warnings,
            "verified_at": timezone.now().isoformat(),
        },
    }

    outcome = gateway.extract_status(payload)
    if verification_errors:
        outcome = "failed"

    verified_transaction = apply_payment_outcome(
        transaction=transaction,
        payload=verification_payload,
        outcome=outcome,
    )
    return verified_transaction


def verify_transaction_by_reference(
    *,
    reference: str,
    gateway_key: str,
    transaction_id: str | None = None,
    source: str,
    provider_status: str | None = None,
) -> PaymentTransaction:
    expire_stale_pending_transactions()
    try:
        transaction = PaymentTransaction.objects.select_related(
            "subscription",
            "user",
            "subscription__plan",
            "flutterwave_record",
        ).get(reference=reference, gateway=gateway_key)
    except PaymentTransaction.DoesNotExist as exc:
        raise ValueError("Payment transaction was not found.") from exc
    if gateway_key == PaymentTransaction.Gateway.FLUTTERWAVE:
        return _verify_flutterwave_transaction(
            transaction=transaction,
            transaction_id=transaction_id,
            source=source,
            provider_status=provider_status,
        )
    return sync_transaction_status(transaction=transaction)


def build_flutterwave_return_url(
    *,
    transaction: PaymentTransaction,
    transaction_id: str | None = None,
    status: str | None = None,
) -> str:
    provider_payload = transaction.provider_payload or {}
    return_url = str(provider_payload.get("return_url") or f"{settings.WEB_URL}/billing/status").strip()
    return append_query_params(
        return_url,
        gateway=transaction.gateway,
        reference=transaction.reference,
        tx_ref=transaction.reference,
        transaction_id=transaction_id or getattr(getattr(transaction, "flutterwave_record", None), "flutterwave_transaction_id", ""),
        status=transaction.status,
    )


def _get_effective_subscription_start(*, subscription: UserSubscription, fallback):
    raw_value = (subscription.metadata or {}).get("effective_starts_at")
    if not raw_value:
        return fallback
    parsed_value = parse_datetime(raw_value)
    if parsed_value is None:
        return fallback
    if timezone.is_naive(parsed_value):
        return timezone.make_aware(parsed_value, timezone.get_current_timezone())
    return parsed_value


def apply_payment_outcome(*, transaction: PaymentTransaction, payload: dict, outcome: str) -> PaymentTransaction:
    if transaction.status == PaymentTransaction.Status.SUCCESSFUL:
        _sync_flutterwave_record(transaction=transaction, payload=payload, status=transaction.status)
        return transaction
    if transaction.status in {
        PaymentTransaction.Status.FAILED,
        PaymentTransaction.Status.CANCELLED,
        PaymentTransaction.Status.EXPIRED,
        PaymentTransaction.Status.ABANDONED,
    } and outcome == "failed":
        _sync_flutterwave_record(transaction=transaction, payload=payload, status=transaction.status)
        return transaction

    if outcome == "success":
        previous_status = transaction.status
        transaction.status = PaymentTransaction.Status.SUCCESSFUL
        transaction.paid_at = transaction.paid_at or timezone.now()
        transaction.provider_payload = payload
        transaction.save(update_fields=["status", "paid_at", "provider_payload", "updated_at"])
        _sync_flutterwave_record(
            transaction=transaction,
            payload=payload,
            status=transaction.status,
            verified=transaction.gateway == PaymentTransaction.Gateway.FLUTTERWAVE,
        )

        subscription = activate_paid_subscription(
            subscription=transaction.subscription,
            starts_at=_get_effective_subscription_start(
                subscription=transaction.subscription,
                fallback=transaction.paid_at,
            ),
        )
        reactivate_corper_account(user=transaction.user, now=transaction.paid_at)
        create_notification(
            recipient=transaction.user,
            notification_type=Notification.Type.PAYMENT_SUCCESS,
            title="Payment successful",
            body=f"Your {subscription.plan.name} subscription is now active.",
            data={"transaction_id": str(transaction.id), "subscription_id": str(subscription.id)},
        )
        log_audit_event(
            actor=transaction.user,
            action="payment.successful",
            target_type="payment_transaction",
            target_id=str(transaction.id),
            metadata={
                "reference": transaction.reference,
                "gateway": transaction.gateway,
                "previous_status": previous_status,
                "subscription_id": str(subscription.id),
            },
        )
        return transaction

    if outcome == "failed":
        _set_terminal_payment_status(
            transaction=transaction,
            status=PaymentTransaction.Status.FAILED,
            payload=payload,
            notification_title="Payment failed",
            notification_body="Your payment could not be confirmed.",
        )
        return transaction

    next_status = (
        PaymentTransaction.Status.PROCESSING
        if transaction.status == PaymentTransaction.Status.PENDING
        else transaction.status
    )
    transaction.status = next_status
    transaction.provider_payload = payload
    transaction.save(update_fields=["status", "provider_payload", "updated_at"])
    _sync_flutterwave_record(
        transaction=transaction,
        payload=payload,
        status=transaction.status,
        verified=transaction.gateway == PaymentTransaction.Gateway.FLUTTERWAVE,
    )
    return transaction


def sync_transaction_status(*, transaction: PaymentTransaction) -> PaymentTransaction:
    if transaction.status == PaymentTransaction.Status.SUCCESSFUL:
        return transaction
    expire_stale_pending_transactions(user=transaction.user)
    transaction.refresh_from_db()
    if transaction.gateway == PaymentTransaction.Gateway.FLUTTERWAVE:
        return _verify_flutterwave_transaction(transaction=transaction, source="status")
    try:
        payload = get_gateway(transaction.gateway).query_payment_status(reference=transaction.reference)
    except NotImplementedError:
        return transaction
    if payload is None:
        return transaction
    outcome = get_gateway(transaction.gateway).extract_status(payload)
    return apply_payment_outcome(transaction=transaction, payload=payload, outcome=outcome)


def process_recorded_webhook_event(*, event_id: str) -> PaymentWebhookEvent:
    event = PaymentWebhookEvent.objects.get(event_id=event_id)
    if event.process_status == PaymentWebhookEvent.ProcessStatus.PROCESSED:
        return event

    gateway = get_gateway(event.gateway)
    payload = event.payload or {}
    reference = gateway.extract_reference(payload)
    try:
        transaction = PaymentTransaction.objects.select_related(
            "subscription",
            "user",
            "subscription__plan",
            "flutterwave_record",
        ).get(reference=reference, gateway=event.gateway)
        if event.gateway == PaymentTransaction.Gateway.FLUTTERWAVE:
            transaction = _verify_flutterwave_transaction(
                transaction=transaction,
                transaction_id=str(_extract_provider_data(payload).get("id") or "").strip() or None,
                source="webhook",
            )
        else:
            outcome = gateway.extract_status(payload)
            apply_payment_outcome(transaction=transaction, payload=payload, outcome=outcome)
    except PaymentTransaction.DoesNotExist as exc:
        _mark_webhook_event_failed(event=event, payload=payload, signature=event.signature)
        raise ValueError("Payment transaction was not found.") from exc
    except ValueError:
        _mark_webhook_event_failed(event=event, payload=payload, signature=event.signature)
        raise
    except Exception:
        _mark_webhook_event_failed(event=event, payload=payload, signature=event.signature)
        raise

    event.process_status = PaymentWebhookEvent.ProcessStatus.PROCESSED
    event.payload = payload
    event.processed_at = timezone.now()
    event.save(update_fields=["process_status", "payload", "processed_at", "updated_at"])
    log_audit_event(
        actor=transaction.user,
        action="payment.webhook_processed",
        target_type="payment_webhook",
        target_id=str(event.id),
        metadata={
            "gateway": event.gateway,
            "event_type": event.event_type,
            "reference": transaction.reference,
            "transaction_id": str(transaction.id),
        },
    )
    return event


def process_webhook(*, gateway_key: str, raw_body: bytes, signature: str):
    from apps.payments.tasks import process_payment_webhook_event_task

    gateway = get_gateway(gateway_key)
    payload = json.loads(raw_body.decode("utf-8"))
    event_id = gateway.extract_event_id(payload)
    event = _store_webhook_event(
        gateway_key=gateway_key,
        event_id=event_id,
        payload=payload,
        signature=signature or "",
    )

    if not gateway.verify_signature(raw_body=raw_body, signature=signature):
        _mark_webhook_event_failed(event=event, payload=payload, signature=signature or "")
        logger.warning("Rejected payment webhook due to invalid signature.", extra={"gateway": gateway_key})
        raise ValueError("Invalid webhook signature.")

    if event.process_status == PaymentWebhookEvent.ProcessStatus.PROCESSED:
        return event

    event.process_status = PaymentWebhookEvent.ProcessStatus.RECEIVED
    event.processed_at = None
    event.save(update_fields=["process_status", "processed_at", "updated_at"])
    process_payment_webhook_event_task.delay(event.event_id)
    event.refresh_from_db()
    return event
