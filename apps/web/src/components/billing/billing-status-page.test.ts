import { describe, expect, it } from "vitest";

import { resolveBillingStatusPaths } from "@/components/billing/billing-status-page";

describe("resolveBillingStatusPaths", () => {
  it("keeps successful corper payments on the companies page while sending Back to billing", () => {
    expect(
      resolveBillingStatusPaths({
        billingPath: "/corper/companies",
        isReactivationFlow: false,
        role: "corper",
      })
    ).toEqual({
      successPath: "/corper/companies",
      backToBillingPath: "/corper/billing",
    });
  });

  it("keeps reactivation payments returning to the tokenized billing page", () => {
    expect(
      resolveBillingStatusPaths({
        billingPath: "/corper/billing?reactivation_token=abc123",
        isReactivationFlow: true,
        role: "corper",
      })
    ).toEqual({
      successPath: "/corper/billing?reactivation_token=abc123",
      backToBillingPath: "/corper/billing?reactivation_token=abc123",
    });
  });
});
