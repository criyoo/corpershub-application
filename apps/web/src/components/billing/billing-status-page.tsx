"use client";

import { useEffect, useState } from "react";

import { useSearchParams } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiFetch, resolveSessionUser } from "@/lib/api";
import { getHostedCheckoutProviderName } from "@/lib/payments";
import { getBillingPathForRole } from "@/lib/subscriptions";


type PaymentStatusResponse = {
  reference: string;
  tx_ref?: string;
  flutterwave_transaction_id?: string;
  gateway: string;
  status: string;
  amount_kobo: number;
  currency: string;
  plan_code: string | null;
  plan_name: string | null;
  role: "company" | "corper" | "admin";
  provider_payload?: {
    checkout?: {
      account_number?: string;
      account_bank_name?: string;
      account_type?: string;
      customer_reference?: string;
      note?: string;
      expires_at?: string;
    } | null;
  } | null;
  attempt_expires_at?: string | null;
  paid_at: string | null;
  verified_at?: string | null;
  created_at: string;
};

const POLLABLE_STATUSES = new Set(["pending", "processing"]);

function formatAmount(amountKobo: number, currency: string) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amountKobo / 100);
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not available yet";
  }
  return new Intl.DateTimeFormat("en-NG", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function getTone(status: string) {
  if (status === "successful") {
    return "success";
  }
  if (status === "failed" || status === "cancelled" || status === "expired" || status === "abandoned") {
    return "warning";
  }
  return "neutral";
}

function getTitle(status: string, isReactivationFlow: boolean) {
  if (status === "successful") {
    return isReactivationFlow ? "Your reactivation payment is confirmed" : "Your payment is confirmed";
  }
  if (status === "failed") {
    return "Your payment could not be confirmed";
  }
  if (status === "cancelled") {
    return "You cancelled this payment";
  }
  if (status === "expired") {
    return "This payment attempt expired";
  }
  if (status === "abandoned") {
    return "This payment attempt was abandoned";
  }
  return "Waiting for payment confirmation";
}

function getDescription(status: string, isReactivationFlow: boolean) {
  if (status === "successful") {
    return isReactivationFlow
      ? "Your corper account has been reactivated. Sign in to continue."
      : "Your subscription is active and your billing plan has been updated.";
  }
  if (status === "failed") {
    return "Your payment did not complete successfully. You can return to billing and try again.";
  }
  if (status === "cancelled") {
    return "No charge was confirmed. Return to billing whenever you are ready to restart checkout.";
  }
  if (status === "expired") {
    return "The payment window expired before confirmation. Return to billing to continue or start again.";
  }
  if (status === "abandoned") {
    return "The attempt was left incomplete. Return to billing to continue or create a new one.";
  }
  return "Awaiting payment confirmation before activating your subscription plan.. Do not close this page!";
}

function getFlutterwaveCheckout(payment: PaymentStatusResponse | null) {
  return payment?.provider_payload?.checkout ?? null;
}

export function resolveBillingStatusPaths({
  billingPath,
  isReactivationFlow,
  role,
}: {
  billingPath: string;
  isReactivationFlow: boolean;
  role: "company" | "corper" | null;
}) {
  const fallbackBillingPath = role ? getBillingPathForRole(role) : "/";
  return {
    successPath: billingPath || fallbackBillingPath,
    backToBillingPath: isReactivationFlow ? billingPath || fallbackBillingPath : fallbackBillingPath,
  };
}

export function BillingStatusPage() {
  const { session, updateSession } = useAuth();
  const searchParams = useSearchParams();
  const reference = (searchParams.get("reference") ?? "").trim();
  const billingPath = searchParams.get("billing_path") ?? "";
  const flow = searchParams.get("flow") ?? "";
  const roleFromUrl = searchParams.get("role") ?? "";
  const gatewayFromUrl = searchParams.get("gateway") ?? "";
  const txRefFromUrl = (searchParams.get("tx_ref") ?? "").trim();
  const flutterwaveTransactionId = (searchParams.get("transaction_id") ?? "").trim();
  const statusFromUrl = (searchParams.get("status") ?? "").trim();
  const isCancelled = searchParams.get("cancelled") === "1";
  const isReactivationFlow = flow === "reactivation";

  const [payment, setPayment] = useState<PaymentStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(reference));

  useEffect(() => {
    if (!reference) {
      setLoading(false);
      setError("Missing payment reference.");
      return;
    }

    let isActive = true;
    let timerId: number | null = null;

    async function loadStatus() {
      try {
        const statusUrl =
          gatewayFromUrl === "flutterwave"
            ? `/payments/transactions/flutterwave/verify/?reference=${encodeURIComponent(
              txRefFromUrl || reference
            )}${flutterwaveTransactionId ? `&transaction_id=${encodeURIComponent(flutterwaveTransactionId)}` : ""}${statusFromUrl ? `&status=${encodeURIComponent(statusFromUrl)}` : ""
            }`
            : `/payments/transactions/status/?reference=${encodeURIComponent(reference)}`;
        const data = await apiFetch<PaymentStatusResponse>(statusUrl, { auth: false });
        if (!isActive) {
          return;
        }
        setPayment(data);
        setError(null);
        setLoading(false);
        if (POLLABLE_STATUSES.has(data.status)) {
          timerId = window.setTimeout(() => {
            void loadStatus();
          }, 4000);
        }
      } catch (statusError) {
        if (!isActive) {
          return;
        }
        setError(statusError instanceof Error ? statusError.message : "Unable to load payment status.");
        setLoading(false);
      }
    }

    void loadStatus();
    return () => {
      isActive = false;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, [flutterwaveTransactionId, gatewayFromUrl, reference, statusFromUrl, txRefFromUrl]);

  const effectiveStatus =
    isCancelled && payment?.status !== "successful"
      ? "cancelled"
      : payment?.status ?? (loading ? "pending" : "failed");
  const resolvedRole =
    payment?.role && payment.role !== "admin"
      ? payment.role
      : roleFromUrl === "company" || roleFromUrl === "corper"
        ? roleFromUrl
        : null;
  const { successPath, backToBillingPath } = resolveBillingStatusPaths({
    billingPath,
    isReactivationFlow,
    role: resolvedRole,
  });
  const checkoutGateway = payment?.gateway ?? gatewayFromUrl;
  const checkoutProviderName = getHostedCheckoutProviderName(checkoutGateway);
  const flutterwaveCheckout = getFlutterwaveCheckout(payment);
  const isFlutterwavePayment = checkoutGateway === "flutterwave";
  const isCorperSuccessFlow = (payment?.role ?? roleFromUrl) === "corper";
  const successCtaLabel = isCorperSuccessFlow ? "Continue to Discover Companies" : "Back to billing";

  useEffect(() => {
    if (effectiveStatus !== "successful" || isReactivationFlow) {
      return;
    }

    let cancelled = false;
    let redirectTimerId: number | null = null;
    const syncSessionAndRedirect = async () => {
      if (session) {
        try {
          const resolvedUser = await resolveSessionUser();
          if (!cancelled && resolvedUser) {
            updateSession({
              ...session,
              user: resolvedUser,
            });
          }
        } catch {
          // Fall back to redirect even if session refresh fails.
        }
      }

      if (!cancelled) {
        redirectTimerId = window.setTimeout(() => {
          if (!cancelled) {
            window.location.assign(successPath);
          }
        }, 1500);
      }
    };

    void syncSessionAndRedirect();

    return () => {
      cancelled = true;
      if (redirectTimerId) {
        window.clearTimeout(redirectTimerId);
      }
    };
  }, [effectiveStatus, isReactivationFlow, session, successPath, updateSession]);

  return (
    <main className="min-h-screen px-4 py-10">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            {isFlutterwavePayment && effectiveStatus !== "successful" ? (
              <Button
                variant="secondary"
                onClick={() => {
                  window.location.assign(backToBillingPath);
                }}
              >
                Back
              </Button>
            ) : null}
            <div>
              <Badge tone={getTone(effectiveStatus)}>
                {effectiveStatus === "successful"
                  ? "Payment complete"
                  : effectiveStatus === "failed"
                    ? "Payment failed"
                    : effectiveStatus === "cancelled"
                      ? "Payment cancelled"
                      : effectiveStatus === "expired"
                        ? "Payment expired"
                        : effectiveStatus === "abandoned"
                          ? "Payment abandoned"
                          : "Payment pending"}
              </Badge>
              <h1 className="mt-4 font-display text-4xl text-white">{getTitle(effectiveStatus, isReactivationFlow)}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-mist">
                {getDescription(effectiveStatus, isReactivationFlow)}
              </p>
            </div>
          </div>
        </div>

        {error ? (
          <Card className="border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to verify payment</h2>
            <p className="mt-3 text-sm text-mist">{error}</p>
          </Card>
        ) : null}

        <Card className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Checkout provider</p>
            <p className="mt-3 text-2xl text-white">{checkoutProviderName}</p>
          </div>
          <div className="rounded-[24px] border border-white/10 bg-[#07140E]/40 p-5">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Transaction details</p>
            <p className="mt-3 text-sm text-white">Reference: {reference || "Missing reference"}</p>
            <p className="mt-2 text-sm text-mist">
              Amount: {payment ? formatAmount(payment.amount_kobo, payment.currency) : "Loading..."}
            </p>
            <p className="mt-2 text-sm text-mist">Plan: {payment?.plan_name ?? "Loading..."}</p>
            <p className="mt-2 text-sm text-mist">Created: {formatDate(payment?.created_at)}</p>
            <p className="mt-2 text-sm text-mist">Attempt expires: {formatDate(payment?.attempt_expires_at)}</p>
            <p className="mt-2 text-sm text-mist">Verified: {formatDate(payment?.verified_at)}</p>
            <p className="mt-2 text-sm text-mist">Paid: {formatDate(payment?.paid_at)}</p>
          </div>
        </Card>

        {checkoutGateway === "flutterwave" && flutterwaveCheckout?.account_number && effectiveStatus !== "successful" ? (
          <Card>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Payment instructions</p>
            <p className="mt-3 text-sm text-white">
              Bank: {flutterwaveCheckout.account_bank_name ?? "Payment partner bank"}
            </p>
            <p className="mt-2 text-sm text-white">Account number: {flutterwaveCheckout.account_number}</p>
            <p className="mt-2 text-sm text-mist">
              Reference: {flutterwaveCheckout.customer_reference ?? payment?.reference ?? reference}
            </p>
            <p className="mt-2 text-sm text-mist">
              Expires: {formatDate(flutterwaveCheckout.expires_at) ?? "Check your payment partner instructions"}
            </p>
            <p className="mt-3 text-sm leading-7 text-mist">
              {flutterwaveCheckout.note ?? "Transfer the exact amount into the account above, then wait here for confirmation."}
            </p>
          </Card>
        ) : null}

        {(effectiveStatus === "pending" || effectiveStatus === "processing") && checkoutGateway === "flutterwave" ? (
          <Card className="border-lime/20 bg-lime/5">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Payment verification note</p>
            <p className="mt-3 text-sm leading-7 text-mist">
              Your access is activated once payment is successfully confirmed.<b />
              Keep this page open or return to billing until payment is confirmed.
            </p>
          </Card>
        ) : null}

        <div className="flex flex-wrap gap-3">
          {effectiveStatus === "successful" ? (
            <Button
              onClick={() => {
                window.location.assign(isReactivationFlow ? "/login/" : successPath);
              }}
            >
              {isReactivationFlow ? "Sign in" : successCtaLabel}
            </Button>
          ) : null}

          {effectiveStatus !== "successful" ? (
            <Button
              variant="secondary"
              onClick={() => {
                window.location.assign(backToBillingPath);
              }}
            >
              Return to billing
            </Button>
          ) : null}
        </div>
      </div>
    </main>
  );
}
