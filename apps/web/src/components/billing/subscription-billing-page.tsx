"use client";

import { useEffect, useState } from "react";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { ApiError, apiFetch, resolveSessionUser, type PaginatedResponse } from "@/lib/api";
import {
  getHostedCheckoutProviderName,
  getHostedCheckoutRedirectMessage,
  getPreferredHostedPaymentGateway,
  launchHostedCheckout,
  type HostedCheckoutPayload,
} from "@/lib/payments";
import type { UserRole } from "@/lib/session";
import {
  type BillingPlan,
  type BillingPlanResponse,
  type BillingSubscriptionResponse,
  formatBillingInterval,
  formatSubscriptionPlanLabel,
  formatSubscriptionStatus,
  getBillingPathForRole,
  resolveCurrentSubscription,
  resolveSubscriptionStatusSnapshot,
} from "@/lib/subscriptions";



type ReactivationResolveResponse = {
  message: string;
  user: {
    email: string;
    role: UserRole;
  };
  billing_path: string;
};

type InitiatePaymentResponse = {
  message?: string;
  subscription_started?: boolean;
  checkout?: HostedCheckoutPayload;
  transaction?: {
    amount_kobo: number;
  };
};

type PaymentAttempt = {
  id: string;
  gateway: string;
  reference: string;
  status: string;
  amount_kobo: number;
  currency: string;
  plan_code: string | null;
  plan_name: string | null;
  provider_payload?: {
    checkout?: HostedCheckoutPayload;
    attempt_state?: {
      expired_at?: string;
      cancelled_at?: string;
      reason?: string;
    };
  } | null;
  attempt_expires_at?: string | null;
  created_at: string;
};

type PricingCardAction = {
  amountDue: number;
  disabled: boolean;
  label: string;
  note: string | null;
};

type PlanChangePrompt = {
  planCode: string;
  currentPlanName: string;
  newPlanName: string;
};

function PlanChangeConfirmModal({
  open,
  prompt,
  onCancel,
  onConfirm,
  confirming,
}: {
  open: boolean;
  prompt: PlanChangePrompt | null;
  onCancel: () => void;
  onConfirm: () => void;
  confirming: boolean;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !confirming) {
        onCancel();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [confirming, onCancel, open]);

  if (!mounted || !open || !prompt) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm"
      role="presentation"
      onClick={() => {
        if (!confirming) {
          onCancel();
        }
      }}
    >
      <div
        className="w-full max-w-lg rounded-3xl border border-white/10 bg-ink/95 p-8 shadow-glow"
        role="dialog"
        aria-modal="true"
        aria-labelledby="plan-change-title"
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <h2 id="plan-change-title" className="font-display text-2xl text-white">
          Change subscription plan?
        </h2>
        <p className="mt-3 text-sm leading-7 text-mist">
          <Badge className="text-[10px] text-lime">WARNING!!!</Badge><b />
          You are currently on a {" "} plan. <b />
          <span className="text-white">{formatSubscriptionPlanLabel(prompt.currentPlanName)}</span> <b />
          Switching to a {" "} plan
          <span className="text-white">{formatSubscriptionPlanLabel(prompt.newPlanName)}</span> will immediately cancel your current plan.<b />
          You will loose any remaining day(s) left on your current plan with no refunds!. <b />
          Your new plan will begin today once payment is confirmed. <b />
        </p>
        <div className="mt-8 flex flex-wrap justify-end gap-3">
          <Button variant="secondary" type="button" disabled={confirming} onClick={onCancel}>
            Keep current plan
          </Button>
          <Button type="button" disabled={confirming} onClick={onConfirm}>
            {confirming ? "Starting checkout..." : "Continue to payment"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return new Intl.DateTimeFormat("en-NG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return new Intl.DateTimeFormat("en-NG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function getBrowseAccessMessage(
  currentPlan: BillingPlan | null,
  currentStatus: string | null,
  hasEndsAt: boolean
) {
  if (currentStatus === "active") {
    return `Active plan, explore!.`;
  }
  if (currentStatus === "cancelled" && hasEndsAt) {
    return `This plan has been cancelled and stays active until its expiry date.`;
  }
  if (currentStatus === "trial") {
    return `Browse companies with trial plan; match score, interest, and chat not available on the trial plan.`;
  }
  if (currentStatus === "pending") {
    return `Your payment is pending verification. Complete the payment and wait for confirmation — your subscription activates on successful confirmation.`;
  }
  if (currentPlan) {
    return `Upgrade to a paid plan to browse companies.`;
  }
  return `No active plan.`;
}

function formatNaira(value: number) {
  return `₦${value.toLocaleString()}`;
}

function formatAmount(amountKobo: number, currency: string) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amountKobo / 100);
}

function formatMonthlyEquivalent(plan: BillingPlan) {
  if (plan.amount_naira === 0) {
    return "Free";
  }

  const monthsByInterval: Record<string, number> = {
    quarterly: 3,
    semiannual: 6,
    yearly: 12,
  };
  const months = monthsByInterval[plan.billing_interval];
  if (!months) {
    return formatNaira(plan.amount_naira);
  }
  return `${formatNaira(Math.round(plan.amount_naira / months))}/mo`;
}

function getPlanDescriptionText(plan: BillingPlan) {
  if (plan.description === "One-off corper payment that unlocks full access for 3 months.") {
    return null;
  }
  if (plan.description === "One-off corper payment that unlocks full access for 6 months.") {
    return null;
  }
  if (plan.description === "One-off corper payment that unlocks full access for 12 months.") {
    return null;
  }
  return plan.description;
}

function formatAmountDueLabel(amountDue: number) {
  return amountDue === 0 ? "Included in your current access" : `Pay now ${formatNaira(amountDue)}`;
}

function getPlanSpotlight(plan: BillingPlan) {
  if (plan.code === "free") {
    return {
      label: "Starter",
      tone: "neutral" as const,
    };
  }
  if (plan.code === "six-months") {
    return {
      label: "Most popular",
      tone: "success" as const,
    };
  }
  if (plan.code === "twelve-months") {
    return {
      label: "Best value",
      tone: "warning" as const,
    };
  }
  return null;
}

function getPaidPlanAction({
  plan,
  currentSubscription,
}: {
  plan: BillingPlan;
  currentSubscription: ReturnType<typeof resolveCurrentSubscription>;
}) {
  if (
    currentSubscription &&
    (currentSubscription.status === "active" ||
      currentSubscription.status === "trial" ||
      (currentSubscription.status === "cancelled" && currentSubscription.ends_at !== null))
  ) {
    const isCurrentPlan = currentSubscription.plan.code === plan.code;
    return {
      disabled: isCurrentPlan,
      label: isCurrentPlan ? "Current Plan" : "Choose Plan",
      amountDue: isCurrentPlan ? 0 : plan.amount_naira,
      note: isCurrentPlan
        ? null
        : "Choosing a new plan cancels your current plan immediately. Payments are non-refundable and the new plan starts today.",
    };
  }

  return {
    disabled: false,
    label: `Choose Plan`,
    amountDue: plan.amount_naira,
    note: null,
  };
}

function PricingPlanCard({
  plan,
  accent,
  statusLabel,
  action,
  layout = "vertical",
  onSelect,
}: {
  plan: BillingPlan;
  accent: {
    label: string;
    tone: "neutral" | "success" | "warning";
  } | null;
  statusLabel?: {
    label: string;
    tone: "neutral" | "success" | "warning";
  } | null;
  action: PricingCardAction;
  layout?: "vertical" | "horizontal";
  onSelect: () => void;
}) {
  const isEmphasized = Boolean(accent && accent.tone !== "neutral") || statusLabel?.tone === "success";
  const description = getPlanDescriptionText(plan);
  const buttonVariant =
    plan.amount_naira === 0 || action.label === "Current Plan" ? "secondary" : "primary";
  const buttonClassName = "h-10 w-full rounded-xl px-4 text-sm";

  if (layout === "horizontal") {
    return (
      <Card
        className={[
          "overflow-hidden p-0 transition duration-200",
          isEmphasized
            ? "border-lime/30 bg-[linear-gradient(135deg,rgba(31,183,102,0.16),rgba(7,20,14,0.92)_42%,rgba(7,20,14,0.96)_100%)] shadow-[0_24px_60px_rgba(17,138,72,0.22)]"
            : "bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(7,20,14,0.92)_42%,rgba(7,20,14,0.96)_100%)]",
        ].join(" ")}
      >
        <div className="grid gap-4 p-5">
          <div className="flex min-h-[24px] flex-wrap items-start gap-2">
            {statusLabel ? <Badge tone={statusLabel.tone} className="text-[8px]">{statusLabel.label}</Badge> : null}
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1fr)_minmax(0,0.62fr)] lg:items-stretch">
            <div className="flex flex-col justify-center">
              <p className="text-xs uppercase tracking-[0.24em] text-mist/80">
                {formatBillingInterval(plan.billing_interval)}
              </p>
              <h3 className="mt-3 font-display text-3xl text-white">
                {formatSubscriptionPlanLabel(plan.name)}
              </h3>
            </div>

            <div className="border-t border-white/10 pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
              <p className="text-xs uppercase tracking-[0.24em] text-mist/80">Features</p>
              <div className="mt-3 space-y-2.5">
                {plan.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-3">
                    <span className="mt-2 h-1.5 w-1.5 rounded-full bg-lime" />
                    <span className="text-xs leading-5 text-mist">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col justify-between border-t border-white/10 pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-mist/80">
                  {action.amountDue > 0 && action.amountDue !== plan.amount_naira ? "Plan price" : "Amount"}
                </p>
                <div className="mt-3 flex items-end gap-2">
                  <span className="font-display text-4xl leading-none text-white">
                    {plan.amount_naira === 0 ? "₦0" : formatNaira(plan.amount_naira)}
                  </span>
                </div>
                <p className="mt-2 text-sm font-semibold text-lime">{formatMonthlyEquivalent(plan)}</p>
                {action.amountDue > 0 && action.amountDue !== plan.amount_naira ? (
                  <p className="mt-2 text-sm font-semibold text-coral">{formatAmountDueLabel(action.amountDue)}</p>
                ) : null}
              </div>

              <Button
                className={[buttonClassName, "mt-4"].join(" ")}
                variant={buttonVariant}
                disabled={action.disabled}
                onClick={onSelect}
              >
                {action.label}
              </Button>
              {action.note ? <p className="mt-3 text-xs leading-5 text-mist">{action.note}</p> : null}
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      className={[
        "flex h-full flex-col overflow-hidden p-0 transition duration-200",
        isEmphasized
          ? "border-lime/30 bg-[linear-gradient(135deg,rgba(31,183,102,0.16),rgba(7,20,14,0.92)_42%,rgba(7,20,14,0.96)_100%)] shadow-[0_24px_60px_rgba(17,138,72,0.22)]"
          : "bg-[linear-gradient(135deg,rgba(255,255,255,0.08),rgba(7,20,14,0.92)_42%,rgba(7,20,14,0.96)_100%)]",
      ].join(" ")}
    >
      <div className="grid h-full grid-rows-[auto_1fr_auto] p-6">
        <div className="flex flex-wrap items-center justify-center gap-2">
          {statusLabel ? <Badge tone={statusLabel.tone} className="text-[8px]">{statusLabel.label}</Badge> : null}
        </div>

        <div className="flex h-full flex-col">
          <div className="grid justify-items-center text-center">
            <h3 className="font-display text-3xl text-white">{formatSubscriptionPlanLabel(plan.name)}</h3>
            {description ? <p className="mt-2 text-xs leading-5 text-mist">{description}</p> : null}
          </div>

          <div className="flex flex-1 flex-col justify-center">
            <div className="mt-6 border-t border-white/10 pt-6 text-center">
              <p className="text-xs uppercase tracking-[0.24em] text-mist/80">{formatBillingInterval(plan.billing_interval)}</p>
              <div className="mt-3 flex min-h-[60px] items-end justify-center gap-2">
                <span className="font-display text-4xl leading-none text-white">
                  {plan.amount_naira === 0 ? "₦0" : formatNaira(plan.amount_naira)}
                </span>
              </div>
              <p className="mt-2 text-sm font-semibold text-lime">{formatMonthlyEquivalent(plan)}</p>
              {action.amountDue > 0 && action.amountDue !== plan.amount_naira ? (
                <p className="mt-2 text-sm font-semibold text-coral">{formatAmountDueLabel(action.amountDue)}</p>
              ) : null}
            </div>
          </div>

          <div className="border-t border-white/10 pt-6">
            <p className="text-xs uppercase tracking-[0.24em] text-mist/80">Features</p>
            <div className="mt-4 space-y-3">
              {plan.features.map((feature) => (
                <div key={feature} className="flex items-start gap-3">
                  <span className="mt-2 h-1.5 w-1.5 rounded-full bg-lime" />
                  <span className="text-xs leading-5 text-mist">{feature}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex min-h-[48px] items-end">
          <div className="w-full">
            <Button
              className={buttonClassName}
              variant={buttonVariant}
              disabled={action.disabled}
              onClick={onSelect}
            >
              {action.label}
            </Button>
            {action.note ? <p className="mt-3 text-xs leading-5 text-mist">{action.note}</p> : null}
          </div>
        </div>

        <div className="flex min-h-[40px] flex-wrap items-end justify-center gap-2 pt-4">
          {accent ? <Badge tone={accent.tone}>{accent.label}</Badge> : null}
        </div>
      </div>
    </Card>
  );
}

function buildBillingStatusUrl({
  billingPath,
  flow,
  role,
  token,
}: {
  billingPath: string;
  flow?: string;
  role: UserRole;
  token?: string;
}) {
  const url = new URL("/billing/status", window.location.origin);
  url.searchParams.set("billing_path", billingPath);
  url.searchParams.set("role", role);
  if (flow) {
    url.searchParams.set("flow", flow);
  }
  if (token) {
    url.searchParams.set("reactivation_token", token);
  }
  return url.toString();
}

function isOpenPaymentAttempt(status: string | null | undefined) {
  return status === "pending" || status === "processing";
}

function ReactivationBillingPage({ token }: { token: string }) {
  const checkoutGateway = getPreferredHostedPaymentGateway();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [details, setDetails] = useState<ReactivationResolveResponse | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function loadReactivationData() {
      setLoading(true);
      setError(null);
      try {
        const [reactivation, planResponse] = await Promise.all([
          apiFetch<ReactivationResolveResponse>("/auth/reactivation/resolve/", {
            auth: false,
            method: "POST",
            body: JSON.stringify({ token }),
          }),
          apiFetch<BillingPlanResponse>("/subscriptions/plans/", { auth: false }),
        ]);

        if (cancelled) {
          return;
        }

        setDetails(reactivation);
        setPlans(
          planResponse.results.filter(
            (plan) => plan.amount_naira > 0 && (plan.applies_to === "corper" || plan.applies_to === "both")
          )
        );
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load reactivation billing.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadReactivationData();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function startPayment(planCode: string) {
    try {
      const response = await apiFetch<{
        checkout: HostedCheckoutPayload;
      }>("/payments/transactions/reactivation/initiate/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          token,
          plan_code: planCode,
          gateway: checkoutGateway,
          callback_url: buildBillingStatusUrl({
            billingPath: `/corper/billing?reactivation_token=${encodeURIComponent(token)}`,
            flow: "reactivation",
            role: "corper",
            token,
          }),
        }),
      });
      toast.success(getHostedCheckoutRedirectMessage(checkoutGateway));
      const started = await launchHostedCheckout(response.checkout);
      if (!started) {
        throw new Error("Hosted checkout is unavailable right now.");
      }
    } catch (paymentError) {
      toast.error(paymentError instanceof Error ? paymentError.message : "Unable to initialize payment.");
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(124,217,161,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,255,255,0.1),_transparent_18%),linear-gradient(180deg,_#134B35_0%,_#0B261B_58%,_#07140E_100%)] px-4 py-10">
      <div className="mx-auto w-full max-w-5xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Badge tone="warning">Reactivation billing</Badge>
            <h1 className="mt-4 font-display text-4xl text-white">Reactivate your corper account</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-mist">
              {details?.message ?? "Choose a paid plan to reactivate your account."}
            </p>
          </div>
          <Link
            href="/login/"
            className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
          >
            Back to sign in
          </Link>
        </div>

        {loading ? (
          <Card>
            <p className="text-sm text-mist">Loading reactivation options...</p>
          </Card>
        ) : null}

        {error ? (
          <Card className="border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to continue</h2>
            <p className="mt-3 text-sm text-mist">{error}</p>
          </Card>
        ) : null}

        {!loading && !error ? (
          <div className="grid gap-4">
            <Card className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
              <div>
                <Badge tone="warning">Free trial unavailable</Badge>
                <h2 className="mt-4 font-display text-3xl text-white">
                  Reactivation is paid-only for this account
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-7 text-mist">
                  Your original 7-day free trial cannot be used again. Subscribe to a paid plan to reactivate
                  browsing and return to your corper dashboard.
                </p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-[#07140E]/40 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Account</p>
                <p className="mt-3 text-lg text-white">{details?.user.email ?? "Corper account"}</p>
                <p className="mt-4 text-sm text-mist">Role: Corper</p>
                <p className="mt-2 text-sm text-mist">Status: Deactivated pending reactivation</p>
                <p className="mt-2 text-sm text-mist">
                  Checkout: {getHostedCheckoutProviderName(checkoutGateway)}
                </p>
              </div>
            </Card>

            <div className="grid gap-3 md:grid-cols-2lg:grid-cols-4">
              {plans.map((plan) => (
                <PricingPlanCard
                  key={plan.id}
                  plan={plan}
                  accent={getPlanSpotlight(plan)}
                  statusLabel={null}
                  action={{
                    amountDue: plan.amount_naira,
                    disabled: false,
                    label: `Choose Plan`,
                    note: null,
                  }}
                  onSelect={() => void startPayment(plan.code)}
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </main>
  );
}

export function SubscriptionBillingPage({ role }: { role: UserRole }) {
  const searchParams = useSearchParams();
  const { hydrated, session, updateSession } = useAuth();
  const checkoutGateway = getPreferredHostedPaymentGateway();
  const [processingPlanCode, setProcessingPlanCode] = useState<string | null>(null);
  const [continuingAttemptId, setContinuingAttemptId] = useState<string | null>(null);
  const [cancellingAttemptId, setCancellingAttemptId] = useState<string | null>(null);
  const [planChangePrompt, setPlanChangePrompt] = useState<PlanChangePrompt | null>(null);
  const reactivationToken = role === "corper" ? searchParams.get("reactivation_token") : null;
  const isPublicReactivationMode = role === "corper" && hydrated && !session && Boolean(reactivationToken);
  const protectedQueryEnabled = hydrated && Boolean(session) && !isPublicReactivationMode;
  const plans = useApiQuery<BillingPlanResponse>("/subscriptions/plans/", protectedQueryEnabled);
  const subscriptions = useApiQuery<BillingSubscriptionResponse>("/subscriptions/me/", protectedQueryEnabled);
  const paymentAttempts = useApiQuery<PaginatedResponse<PaymentAttempt>>(
    "/payments/transactions/attempts/",
    protectedQueryEnabled,
    10000
  );
  const successPath = role === "corper" ? "/corper/companies" : getBillingPathForRole(role);

  if (isPublicReactivationMode && reactivationToken) {
    return <ReactivationBillingPage token={reactivationToken} />;
  }

  const currentSubscription = resolveCurrentSubscription(subscriptions.data?.results ?? []);
  const statusSubscription = resolveSubscriptionStatusSnapshot(subscriptions.data?.results ?? []);
  const openAttempts = (paymentAttempts.data?.results ?? []).filter((attempt) => isOpenPaymentAttempt(attempt.status));
  const pendingAttemptForPlan = (planCode: string) =>
    openAttempts.find((attempt) => attempt.plan_code === planCode) ?? null;
  const otherPendingAttemptExists = (planCode: string) =>
    openAttempts.some((attempt) => attempt.plan_code !== planCode);
  const freePlan = plans.data?.results.find((plan) => plan.code === "free") ?? null;
  const paidPlans = (plans.data?.results ?? []).filter((plan) => plan.code !== "free");
  const currentPlan = plans.data?.results.find((plan) => plan.code === currentSubscription?.plan.code) ?? null;
  const currentStatus = currentSubscription?.status ?? null;
  const browseUnlocked =
    currentStatus === "active" ||
    currentStatus === "trial" ||
    (currentStatus === "cancelled" && currentSubscription?.ends_at !== null);

  async function continuePayment(attempt: PaymentAttempt) {
    const checkout = attempt.provider_payload?.checkout;
    if (!checkout) {
      toast.error("This payment attempt can no longer be continued.");
      return;
    }

    try {
      setContinuingAttemptId(attempt.id);
      toast.success(getHostedCheckoutRedirectMessage(checkoutGateway));
      const started = await launchHostedCheckout(checkout);
      if (!started) {
        throw new Error("Hosted checkout is unavailable right now.");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to continue payment.");
    } finally {
      setContinuingAttemptId(null);
    }
  }

  async function cancelAttempt(attemptId: string) {
    try {
      setCancellingAttemptId(attemptId);
      await apiFetch(`/payments/transactions/${attemptId}/cancel/`, {
        method: "POST",
      });
      toast.success("Pending payment cancelled.");
      await Promise.all([paymentAttempts.refetch(), subscriptions.refetch()]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to cancel payment.");
    } finally {
      setCancellingAttemptId(null);
    }
  }

  function requestPayment(planCode: string) {
    const selectedPlan = plans.data?.results.find((plan) => plan.code === planCode) ?? null;
    const hasCurrentPaidPlan =
      currentSubscription &&
      currentSubscription.plan.amount_naira > 0 &&
      (currentSubscription.status === "active" ||
        (currentSubscription.status === "cancelled" && currentSubscription.ends_at !== null));

    if (hasCurrentPaidPlan && currentSubscription.plan.code !== planCode && selectedPlan) {
      setPlanChangePrompt({
        planCode,
        currentPlanName: currentSubscription.plan.name,
        newPlanName: selectedPlan.name,
      });
      return;
    }

    void startPayment(planCode);
  }

  async function startPayment(planCode: string) {
    try {
      setProcessingPlanCode(planCode);

      const response = await apiFetch<InitiatePaymentResponse>("/payments/transactions/initiate/", {
        method: "POST",
        body: JSON.stringify({
          plan_code: planCode,
          gateway: checkoutGateway,
          callback_url: buildBillingStatusUrl({
            billingPath: successPath,
            role,
          }),
        }),
      });
      if (response.subscription_started) {
        toast.success(response.message ?? "Your subscription is now active.");
        await Promise.all([subscriptions.refetch(), paymentAttempts.refetch()]);
        if (role === "corper") {
          if (session) {
            try {
              const resolvedUser = await resolveSessionUser();
              if (resolvedUser) {
                updateSession({
                  ...session,
                  user: resolvedUser,
                });
              }
            } catch {
              // Continue to redirect even if the session refresh fails.
            }
          }
          window.location.assign(successPath);
          return;
        }
        return;
      }

      toast.success(getHostedCheckoutRedirectMessage(checkoutGateway));
      await Promise.all([subscriptions.refetch(), paymentAttempts.refetch()]);
      const started = await launchHostedCheckout(response.checkout);
      if (!started) {
        throw new Error("Hosted checkout is unavailable right now.");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await paymentAttempts.refetch();
      }
      toast.error(error instanceof Error ? error.message : "Unable to initialize payment.");
    } finally {
      setProcessingPlanCode(null);
    }
  }

  return (
    <DashboardShell role={role} title="Billing and subscriptions">
      <PlanChangeConfirmModal
        open={Boolean(planChangePrompt)}
        prompt={planChangePrompt}
        confirming={Boolean(planChangePrompt && processingPlanCode === planChangePrompt.planCode)}
        onCancel={() => {
          if (!processingPlanCode) {
            setPlanChangePrompt(null);
          }
        }}
        onConfirm={() => {
          if (!planChangePrompt || processingPlanCode) {
            return;
          }
          const planCode = planChangePrompt.planCode;
          setPlanChangePrompt(null);
          void startPayment(planCode);
        }}
      />
      <div className="grid gap-4">
        <Card className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
<Badge tone={browseUnlocked ? "success" : "warning"}>
               {browseUnlocked ? "Browse unlocked" : "Browse locked"}
             </Badge>
             <h2 className="mt-4 font-display text-2xl text-white">
               Plan: {formatSubscriptionPlanLabel(currentSubscription?.plan.name)}
             </h2>
             <p className="mt-3 max-w-1xl text-sm leading-7 text-mist">
               {getBrowseAccessMessage(currentPlan, currentStatus, Boolean(currentSubscription?.ends_at))}
             </p>
          </div>
          <div className="rounded-[24px] border border-white/10 bg-[#07140E]/40 p-5">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Current status</p>
            <p className="mt-3 text-lg text-white">
              {statusSubscription?.status ? formatSubscriptionStatus(statusSubscription.status) : "Not started"}
            </p>
            <p className="mt-4 text-sm text-mist">
              Started: {formatDate(statusSubscription?.starts_at) ?? "Not available"}
            </p>
            <p className="mt-2 text-sm text-mist">
              Ends: {formatDate(statusSubscription?.ends_at) ?? "No end date yet"}
            </p>
          </div>
        </Card>

        {subscriptions.error ? (
          <Card className="border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to load your subscription records</h2>
            <p className="mt-3 text-sm text-mist">{subscriptions.error}</p>
          </Card>
        ) : null}

        {plans.error ? (
          <Card className="border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to load plans</h2>
            <p className="mt-3 text-sm text-mist">{plans.error}</p>
          </Card>
        ) : null}

        {openAttempts.length ? (
          <Card className="grid gap-4">
            <div>
              <Badge tone="warning">Pending payment</Badge>
              <h2 className="mt-4 font-display text-2xl text-white">
                You can continue, cancel, or switch plans after cancelling
              </h2>
              <p className="mt-3 text-sm leading-7 text-mist">
                Payment attempts are not permanent.<br/>
                If checkout was interrupted, continue the attempt below or cancel it and start again.
              </p>
            </div>

            <div className="grid gap-3">
              {openAttempts.map((attempt) => (
                <div
                  key={attempt.id}
                  className="rounded-[24px] border border-white/10 bg-[#07140E]/40 p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-lime">Attempt</p>
                      <p className="mt-3 text-lg text-white">
                        {formatSubscriptionPlanLabel(attempt.plan_name)}
                      </p>
                      <p className="mt-2 text-sm text-mist">
                        {formatAmount(attempt.amount_kobo, attempt.currency)} · Ref {attempt.reference}
                      </p>
                      <p className="mt-2 text-sm text-mist">
                        Expires: {formatDate(attempt.attempt_expires_at ?? null)}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <Button
                        disabled={continuingAttemptId === attempt.id}
                        onClick={() => void continuePayment(attempt)}
                      >
                        {continuingAttemptId === attempt.id ? "Redirecting to payment..." : "Continue Payment"}
                      </Button>
                      <Button
                        variant="secondary"
                        disabled={cancellingAttemptId === attempt.id}
                        onClick={() => void cancelAttempt(attempt.id)}
                      >
                        {cancellingAttemptId === attempt.id ? "Cancelling..." : "Cancel and Start Again"}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => {
                          document.getElementById("billing-plan-grid")?.scrollIntoView({
                            behavior: "smooth",
                            block: "start",
                          });
                        }}
                      >
                        Choose Another Plan
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {freePlan ? (() => {
          const subscriptionHistoryLoaded = Boolean(subscriptions.data);
          const hasSubscriptionHistory = (subscriptions.data?.results.length ?? 0) > 0;
          const isCurrentPlan =
            currentSubscription?.plan.code === freePlan.code &&
            (currentSubscription.status === "active" ||
              currentSubscription.status === "trial" ||
              (currentSubscription.status === "cancelled" && currentSubscription.ends_at !== null));
          const canStartFreeTrial =
            role === "corper" && subscriptionHistoryLoaded && !hasSubscriptionHistory;
          const statusLabel = isCurrentPlan ? { label: "Current plan", tone: "success" as const } : null;
          const action: PricingCardAction = {
            amountDue: 0,
            disabled: !canStartFreeTrial || processingPlanCode === freePlan.code || openAttempts.length > 0,
            label:
              currentSubscription?.status === "trial"
                ? "Current Plan"
                : processingPlanCode === freePlan.code
                  ? "Activating..."
                  : openAttempts.length > 0
                    ? "Pending payment exists"
                    : !subscriptionHistoryLoaded
                      ? "Checking eligibility"
                      : canStartFreeTrial
                        ? "Choose Plan"
                        : "Free trial used",
            note:
              currentSubscription?.status === "trial"
                ? " "
                : openAttempts.length > 0
                  ? "Cancel your pending payment attempt before starting the free trial."
                  : canStartFreeTrial
                    ? "Unlock 7 days of free browsing."
                    : "Free trial already used up.",
          };

          return (
            <PricingPlanCard
              key={freePlan.id}
              plan={freePlan}
              accent={getPlanSpotlight(freePlan)}
              statusLabel={statusLabel}
              action={action}
              layout="horizontal"
              onSelect={() => requestPayment(freePlan.code)}
            />
          );
        })() : null}

        <div id="billing-plan-grid" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {paidPlans.map((plan) => {
            const isCurrentPlan =
              currentSubscription?.plan.code === plan.code &&
              (currentSubscription.status === "active" ||
                currentSubscription.status === "trial" ||
                (currentSubscription.status === "cancelled" && currentSubscription.ends_at !== null));
            const paidPlanAction = getPaidPlanAction({
              plan,
              currentSubscription,
            });
            const action = isCurrentPlan
              ? {
                ...paidPlanAction,
                disabled: true,
                label: "Current Plan",
                note: null,
              }
              : processingPlanCode === plan.code
                ? {
                  ...paidPlanAction,
                  disabled: true,
                  label: "Redirecting to payment...",
                  note: "Your payment attempt is being prepared.",
                }
                : pendingAttemptForPlan(plan.code)
                  ? {
                    ...paidPlanAction,
                    disabled: continuingAttemptId === pendingAttemptForPlan(plan.code)?.id,
                    label:
                      continuingAttemptId === pendingAttemptForPlan(plan.code)?.id
                        ? "Redirecting to payment..."
                        : "Continue Payment",
                    note: "You already have a pending payment attempt for this plan.",
                  }
                  : otherPendingAttemptExists(plan.code)
                    ? {
                      ...paidPlanAction,
                      disabled: true,
                      label: "Pending payment exists",
                      note: "Cancel your current pending payment before starting this plan.",
                    }
                    : {
                      ...paidPlanAction,
                      note: null,
                    };
            const statusLabel = isCurrentPlan
              ? { label: "Current plan", tone: "success" as const }
              : pendingAttemptForPlan(plan.code)
                ? { label: "Awaiting payment", tone: "warning" as const }
                : null;
            return (
              <PricingPlanCard
                key={plan.id}
                plan={plan}
                accent={getPlanSpotlight(plan)}
                statusLabel={statusLabel}
                action={action}
                layout="vertical"
                onSelect={() => {
                  const existingAttempt = pendingAttemptForPlan(plan.code);
                  if (existingAttempt) {
                    void continuePayment(existingAttempt);
                    return;
                  }
                  requestPayment(plan.code);
                }}
              />
            );
          })}
        </div>

        <Card>
          <h2 className="font-display text-xl text-white">Subscription history</h2>
          <div className="mt-4 space-y-3">
            {subscriptions.data?.results.length ? (
              [...subscriptions.data.results]
                .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
                .map((subscription) => (
                  <div
                    key={subscription.id}
                    className="rounded-[20px] border border-white/10 bg-[#07140E]/40 px-4 py-3"
                  >
                    <p className="text-sm text-white">
                      {formatSubscriptionPlanLabel(subscription.plan.name)} -{" "}
                      {formatSubscriptionStatus(subscription.status)}
                    </p>
                    <p className="mt-1 text-xs text-mist">
                      Event time: {formatDateTime(subscription.created_at) ?? "Not available"}
                    </p>
                  </div>
                ))
            ) : (
              <p className="text-sm text-mist">Your subscription records will appear here.</p>
            )}
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}
