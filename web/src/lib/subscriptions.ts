import type { UserRole } from "@/lib/session";

export type BillingPlan = {
  id: string;
  code: string;
  name: string;
  amount_naira: number;
  description: string;
  billing_interval: string;
  applies_to: string;
  features: string[];
};

export type BillingPlanResponse = {
  count: number;
  results: BillingPlan[];
};

export type BillingSubscription = {
  id: string;
  status: string;
  starts_at: string;
  ends_at: string | null;
  created_at: string;
  plan: {
    code: string;
    name: string;
    amount_naira: number;
    billing_interval: string;
  };
};

export type BillingSubscriptionResponse = {
  count: number;
  results: BillingSubscription[];
};

export function formatSubscriptionStatus(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatBillingInterval(value: string) {
  if (value === "trial") {
    return "7 days";
  }
  if (value === "quarterly") {
    return "3 months";
  }
  if (value === "semiannual") {
    return "6 months";
  }
  if (value === "yearly") {
    return "12 months";
  }
  return formatSubscriptionStatus(value);
}

export function formatSubscriptionPlanLabel(name: string | null | undefined) {
  const normalized = (name ?? "").trim();
  if (!normalized) {
    return "No subscription yet";
  }

  return normalized.replace(/^(corper|company)\s+/i, "");
}

export function resolveCurrentSubscription(subscriptions: BillingSubscription[]) {
  const activeSubscription = subscriptions.find(
    (subscription) => subscription.status === "active"
  );
  if (activeSubscription) {
    return activeSubscription;
  }

  const trialSubscription = subscriptions.find(
    (subscription) => subscription.status === "trial"
  );
  if (trialSubscription) {
    return trialSubscription;
  }

  // Only consider cancelled subscriptions that were once active (have ends_at set)
  const activeCancelledSubscription = subscriptions.find(
    (subscription) => subscription.status === "cancelled" && subscription.ends_at !== null
  );
  if (activeCancelledSubscription) {
    return activeCancelledSubscription;
  }

  // No valid current subscription found
  return null;
}

export function resolveSubscriptionStatusSnapshot(subscriptions: BillingSubscription[]) {
  const active = subscriptions.find((subscription) => subscription.status === "active");
  const trial = subscriptions.find((subscription) => subscription.status === "trial");
  const cancelled = subscriptions.find(
    (subscription) => subscription.status === "cancelled" && subscription.ends_at !== null
  );

  const current = active ?? trial ?? cancelled;
  if (current?.ends_at) {
    return current;
  }

  // If no valid current subscription, return the latest subscription with ends_at for status info
  // This covers the case where there's a cancelled-pending that needs history display
  const latestCompletedSubscription =
    subscriptions.find((subscription) => Boolean(subscription.ends_at)) ?? null;

  // If still no valid subscription, return the latest subscription anyway for display
  // (e.g., to show cancelled-pending in status section)
  return latestCompletedSubscription ?? current ?? subscriptions[0] ?? null;
}

export function getBillingPathForRole(role: UserRole) {
  if (role === "corper") {
    return "/corper/billing";
  }
  if (role === "company") {
    return "/company/dashboard";
  }
  return "/admin/overview";
}

export function isBrowseRestrictionMessage(message: string | null | undefined) {
  const normalized = (message ?? "").toLowerCase();
  return (
    normalized.includes("free trial has expired") ||
    normalized.includes("continue browsing") ||
    normalized.includes("choose a subscription plan") ||
    normalized.includes("payment is pending") ||
    normalized.includes("paid plans only") ||
    normalized.includes("subscribe to continue")
  );
}

export function hasPaidCorperAccess(subscriptions: BillingSubscription[]) {
  return subscriptions.some(
    (subscription) =>
      subscription.plan.amount_naira > 0 &&
      (subscription.status === "active" ||
        (subscription.status === "cancelled" && subscription.ends_at !== null))
  );
}

export function getCorperPlanRank(planCode: string | null | undefined) {
  if (planCode === "free") {
    return 0;
  }
  if (planCode === "three-months") {
    return 1;
  }
  if (planCode === "six-months") {
    return 2;
  }
  if (planCode === "twelve-months") {
    return 3;
  }
  return null;
}

export function resolveLatestPaidSubscription(subscriptions: BillingSubscription[]) {
  return (
    subscriptions.find(
      (subscription) => subscription.plan.amount_naira > 0 && subscription.status !== "past_due"
    ) ?? null
  );
}

export function isPaidAccessRequiredMessage(message: string | null | undefined) {
  const normalized = (message ?? "").toLowerCase();
  return (
    normalized.includes("paid corper plans only") ||
    normalized.includes("subscribe to continue") ||
    normalized.includes("needs an active paid plan before chat can start")
  );
}
