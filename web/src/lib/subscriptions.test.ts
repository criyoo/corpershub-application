import { describe, expect, it } from "vitest";

import { resolveCurrentSubscription, resolveSubscriptionStatusSnapshot, hasPaidCorperAccess } from "@/lib/subscriptions";

describe("resolveCurrentSubscription", () => {
  it("returns active subscription as current", () => {
    const subscriptions = [
      { id: "1", status: "active", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result?.status).toBe("active");
  });

  it("returns trial subscription as current when no active", () => {
    const subscriptions = [
      { id: "1", status: "trial", starts_at: "2024-01-01", ends_at: "2024-01-08", created_at: "2024-01-01", plan: { code: "free", name: "Free Trial", amount_naira: 0, billing_interval: "trial" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result?.status).toBe("trial");
  });

  it("returns cancelled subscription with ends_at as current", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: "2025-01-01", created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result?.status).toBe("cancelled");
    expect(result?.ends_at).toBe("2025-01-01");
  });

  it("does NOT return cancelled subscription without ends_at as current", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result).toBeNull();
  });

  it("returns previous active subscription when new plan payment is cancelled", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
      { id: "2", status: "active", starts_at: "2023-06-01", ends_at: "2023-12-01", created_at: "2023-06-01", plan: { code: "three-months", name: "Three Months", amount_naira: 3000, billing_interval: "quarterly" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result?.status).toBe("active");
    expect(result?.plan.code).toBe("three-months");
  });

  it("returns null when only pending subscriptions exist", () => {
    const subscriptions = [
      { id: "1", status: "pending", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveCurrentSubscription(subscriptions);
    expect(result).toBeNull();
  });
});

describe("resolveSubscriptionStatusSnapshot", () => {
  it("returns active subscription when has ends_at", () => {
    const subscriptions = [
      { id: "1", status: "active", starts_at: "2024-01-01", ends_at: "2025-01-01", created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveSubscriptionStatusSnapshot(subscriptions);
    expect(result?.status).toBe("active");
    expect(result?.ends_at).toBe("2025-01-01");
  });

  it("returns latest completed subscription when current has no ends_at", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
      { id: "2", status: "active", starts_at: "2023-06-01", ends_at: "2023-12-01", created_at: "2023-06-01", plan: { code: "three-months", name: "Three Months", amount_naira: 3000, billing_interval: "quarterly" } },
    ];
    const result = resolveSubscriptionStatusSnapshot(subscriptions);
    expect(result?.id).toBe("2");
    expect(result?.ends_at).toBe("2023-12-01");
  });

  it("returns cancelled-pending subscription for status display when no other history exists", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    const result = resolveSubscriptionStatusSnapshot(subscriptions);
    // Returns the cancelled-pending for status display purposes
    expect(result?.status).toBe("cancelled");
    expect(result?.ends_at).toBeNull();
  });
});

describe("hasPaidCorperAccess", () => {
  it("returns true for active paid subscription", () => {
    const subscriptions = [
      { id: "1", status: "active", starts_at: "2024-01-01", ends_at: "2025-01-01", created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    expect(hasPaidCorperAccess(subscriptions)).toBe(true);
  });

  it("returns true for cancelled paid subscription that was once active", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: "2025-01-01", created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    expect(hasPaidCorperAccess(subscriptions)).toBe(true);
  });

  it("returns false for cancelled paid subscription that was never active", () => {
    const subscriptions = [
      { id: "1", status: "cancelled", starts_at: "2024-01-01", ends_at: null, created_at: "2024-01-01", plan: { code: "six-months", name: "Six Months", amount_naira: 5000, billing_interval: "semiannual" } },
    ];
    expect(hasPaidCorperAccess(subscriptions)).toBe(false);
  });

  it("returns false for trial subscription", () => {
    const subscriptions = [
      { id: "1", status: "trial", starts_at: "2024-01-01", ends_at: "2024-01-08", created_at: "2024-01-01", plan: { code: "free", name: "Free Trial", amount_naira: 0, billing_interval: "trial" } },
    ];
    expect(hasPaidCorperAccess(subscriptions)).toBe(false);
  });
});