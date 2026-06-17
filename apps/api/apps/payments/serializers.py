from rest_framework import serializers

from apps.common.utils import mask_identifier
from apps.accounts.account_lifecycle import get_reactivation_user
from apps.payments.models import PaymentTransaction
from apps.payments.services import get_payment_attempt_expires_at


class InitiatePaymentSerializer(serializers.Serializer):
    plan_code = serializers.SlugField()
    gateway = serializers.ChoiceField(choices=PaymentTransaction.Gateway.choices)
    callback_url = serializers.URLField(required=False)


class ReactivationPaymentSerializer(InitiatePaymentSerializer):
    token = serializers.CharField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs["user"] = get_reactivation_user(token=attrs["token"])
        return attrs


class PaymentTransactionSerializer(serializers.ModelSerializer):
    plan_code = serializers.CharField(source="subscription.plan.code", read_only=True)
    plan_name = serializers.CharField(source="subscription.plan.name", read_only=True)
    tx_ref = serializers.SerializerMethodField()
    flutterwave_transaction_id = serializers.SerializerMethodField()
    customer_email = serializers.SerializerMethodField()
    verified_at = serializers.SerializerMethodField()
    attempt_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "gateway",
            "reference",
            "status",
            "amount_kobo",
            "currency",
            "plan_code",
            "plan_name",
            "tx_ref",
            "flutterwave_transaction_id",
            "customer_email",
            "provider_payload",
            "verified_at",
            "attempt_expires_at",
            "paid_at",
            "created_at",
        )

    def get_tx_ref(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.tx_ref if record else obj.reference

    def get_flutterwave_transaction_id(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.flutterwave_transaction_id if record else ""

    def get_customer_email(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.customer_email if record else obj.user.email

    def get_verified_at(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.verified_at if record else None

    def get_attempt_expires_at(self, obj):
        return get_payment_attempt_expires_at(created_at=obj.created_at)


class PaymentTransactionStatusSerializer(serializers.ModelSerializer):
    plan_code = serializers.CharField(source="subscription.plan.code", read_only=True)
    plan_name = serializers.CharField(source="subscription.plan.name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    provider_payload = serializers.JSONField(read_only=True)
    tx_ref = serializers.SerializerMethodField()
    flutterwave_transaction_id = serializers.SerializerMethodField()
    verified_at = serializers.SerializerMethodField()
    attempt_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = (
            "reference",
            "gateway",
            "status",
            "amount_kobo",
            "currency",
            "plan_code",
            "plan_name",
            "role",
            "tx_ref",
            "flutterwave_transaction_id",
            "provider_payload",
            "verified_at",
            "attempt_expires_at",
            "paid_at",
            "created_at",
        )

    def get_tx_ref(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.tx_ref if record else obj.reference

    def get_flutterwave_transaction_id(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.flutterwave_transaction_id if record else ""

    def get_verified_at(self, obj):
        record = getattr(obj, "flutterwave_record", None)
        return record.verified_at if record else None

    def get_attempt_expires_at(self, obj):
        return get_payment_attempt_expires_at(created_at=obj.created_at)


class FlutterwaveSettlementAccountSerializer(serializers.Serializer):
    provider = serializers.CharField(read_only=True)
    configured = serializers.BooleanField(read_only=True)
    bank_name = serializers.CharField(read_only=True)
    account_number = serializers.CharField(read_only=True)
    account_number_masked = serializers.SerializerMethodField()
    dashboard_configuration_required = serializers.BooleanField(read_only=True)

    def get_account_number_masked(self, obj):
        return mask_identifier(obj.get("account_number"), prefix=2, suffix=2)
