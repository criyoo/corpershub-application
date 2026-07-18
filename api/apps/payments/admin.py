from django.contrib import admin

from apps.payments.models import FlutterwavePaymentRecord, PaymentTransaction, PaymentWebhookEvent


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reference",
        "gateway",
        "status",
        "amount_kobo",
        "currency",
        "user",
        "paid_at",
        "created_at",
    )
    list_filter = ("gateway", "status", "currency", "created_at")
    search_fields = ("reference", "user__email", "idempotency_key")
    readonly_fields = ("paid_at", "provider_payload", "created_at", "updated_at")


@admin.register(FlutterwavePaymentRecord)
class FlutterwavePaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "internal_payment",
        "tx_ref",
        "flutterwave_transaction_id",
        "status",
        "amount",
        "currency",
        "customer_email",
        "verified_at",
        "created_at",
    )
    list_filter = ("status", "currency", "verified_at", "created_at")
    search_fields = ("tx_ref", "flutterwave_transaction_id", "customer_email", "internal_payment__reference")
    readonly_fields = ("created_at", "updated_at", "verified_at")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "gateway", "event_type", "process_status", "processed_at", "created_at")
    list_filter = ("gateway", "process_status", "event_type", "created_at")
    search_fields = ("event_id", "signature")
    readonly_fields = ("payload", "processed_at", "created_at", "updated_at")
