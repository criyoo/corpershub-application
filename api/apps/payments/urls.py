from django.urls import path

from apps.payments.views import (
    CancelPaymentAttemptAPIView,
    FlutterwaveSettlementAccountAdminAPIView,
    FlutterwaveRedirectAPIView,
    FlutterwaveTransactionVerifyAPIView,
    InitiatePaymentAPIView,
    PaymentAttemptListAPIView,
    PaymentTransactionAdminListAPIView,
    PaymentTransactionDetailAPIView,
    PaymentTransactionStatusAPIView,
    PaymentWebhookAPIView,
    ReactivationPaymentAPIView,
    TriggerStalePaymentExpiryAPIView,
)

urlpatterns = [
    path("transactions/initiate/", InitiatePaymentAPIView.as_view(), name="payment-initiate"),
    path("transactions/attempts/", PaymentAttemptListAPIView.as_view(), name="payment-attempt-list"),
    path("transactions/<uuid:pk>/cancel/", CancelPaymentAttemptAPIView.as_view(), name="payment-attempt-cancel"),
    path(
        "transactions/flutterwave/redirect/",
        FlutterwaveRedirectAPIView.as_view(),
        name="payment-flutterwave-redirect",
    ),
    path(
        "transactions/flutterwave/verify/",
        FlutterwaveTransactionVerifyAPIView.as_view(),
        name="payment-flutterwave-verify",
    ),
    path(
        "transactions/reactivation/initiate/",
        ReactivationPaymentAPIView.as_view(),
        name="payment-reactivation-initiate",
    ),
    path("transactions/status/", PaymentTransactionStatusAPIView.as_view(), name="payment-transaction-status"),
    path("transactions/<uuid:pk>/", PaymentTransactionDetailAPIView.as_view(), name="payment-transaction-detail"),
    path(
        "admin/settlement-account/",
        FlutterwaveSettlementAccountAdminAPIView.as_view(),
        name="payment-admin-settlement-account",
    ),
    path("admin/transactions/", PaymentTransactionAdminListAPIView.as_view(), name="payment-admin-list"),
    path(
        "internal/expire-stale/",
        TriggerStalePaymentExpiryAPIView.as_view(),
        name="payment-expire-stale-trigger",
    ),
    path("webhooks/<str:gateway>/", PaymentWebhookAPIView.as_view(), name="payment-webhook"),
]
