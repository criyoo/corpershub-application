import { describe, expect, it } from "vitest";

import {
  dashboardPathForRole,
  defaultAppPathForUser,
  isBillingRouteForRole,
  isDiscoveryRouteForRole,
  loginPathForRole,
  normalizeAppPath,
  normalizeProfilePath,
} from "@/lib/session";

describe("dashboardPathForRole", () => {
  it("maps company users to the company workspace", () => {
    expect(dashboardPathForRole("company")).toBe("/company/corpers");
  });

  it("maps corper users to the corper workspace", () => {
    expect(dashboardPathForRole("corper")).toBe("/corper/dashboard");
  });

  it("maps admin users to the admin workspace", () => {
    expect(dashboardPathForRole("admin")).toBe("/admin/overview");
  });
});

describe("loginPathForRole", () => {
  it("routes admins to the dedicated admin login page", () => {
    expect(loginPathForRole("admin")).toBe("/admin/login");
  });

  it("keeps user roles on the shared sign-in page", () => {
    expect(loginPathForRole("company")).toBe("/login/");
    expect(loginPathForRole("corper")).toBe("/login/");
  });
});

describe("defaultAppPathForUser", () => {
  it("routes first-time corpers to verification before billing", () => {
    expect(
      defaultAppPathForUser({
        id: "1a",
        email: "newcorper@example.com",
        role: "corper",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/corper/verification",
        needs_subscription_selection: true,
      })
    ).toBe("/corper/verification");
  });

  it("keeps incomplete corpers on profile before billing", () => {
    expect(
      defaultAppPathForUser({
        id: "1b",
        email: "verifiedcorper@example.com",
        role: "corper",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/corper/profile/",
        needs_subscription_selection: true,
      })
    ).toBe("/corper/profile");
  });

  it("routes unverified company users to the verification page", () => {
    expect(
      defaultAppPathForUser({
        id: "1",
        email: "company@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/company/profile",
        company_verification_status: "unsubmitted",
      })
    ).toBe("/company/verification");
  });

  it("routes corpers with verification and subscription access to discover companies", () => {
    expect(
      defaultAppPathForUser({
        id: "2",
        email: "corper@example.com",
        role: "corper",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: true,
        profile_path: "/corper/profile",
        needs_subscription_selection: false,
      })
    ).toBe("/corper/companies");
  });

  it("routes incomplete corper users to the verification page when documents are pending", () => {
    expect(
      defaultAppPathForUser({
        id: "2b",
        email: "corper@example.com",
        role: "corper",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/corper/verification"
      })
    ).toBe("/corper/verification");
  });

  it("routes verified company users with completed profiles to corper discovery", () => {
    expect(
      defaultAppPathForUser({
        id: "3",
        email: "company@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: true,
        profile_path: "/company/corpers",
        company_verification_status: "verified",
      })
    ).toBe("/company/corpers");
  });

  it("routes verified company users with incomplete profiles to the profile page", () => {
    expect(
      defaultAppPathForUser({
        id: "3b",
        email: "pendingcompany@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/company/profile",
        company_verification_status: "verified",
      })
    ).toBe("/company/profile");
  });

  it("preserves the company terms step after verification", () => {
    expect(
      defaultAppPathForUser({
        id: "3c",
        email: "pendingcompany@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/company/profile/terms",
        company_verification_status: "verified",
      })
    ).toBe("/company/profile/terms");
  });

  it("routes non-verified company users back to the verification page", () => {
    expect(
      defaultAppPathForUser({
        id: "3d",
        email: "pendingcompany@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: true,
        profile_path: "/company/corpers",
        company_verification_status: "pending",
      })
    ).toBe("/company/verification");
  });

  it("normalizes legacy company profile redirects", () => {
    expect(
      defaultAppPathForUser({
        id: "4",
        email: "company@example.com",
        role: "company",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false,
        profile_path: "/business/profile",
        company_verification_status: "rejected",
      })
    ).toBe("/company/verification");
  });

  it("falls back to the verification page for incomplete corpers with missing profile paths", () => {
    expect(
      defaultAppPathForUser({
        id: "5",
        email: "corper@example.com",
        role: "corper",
        email_verified: true,
        is_active: true,
        created_at: "2026-03-10T00:00:00Z",
        profile_completed: false
      })
    ).toBe("/corper/verification");
  });
});

describe("normalizeProfilePath", () => {
  it("strips trailing slashes from app paths", () => {
    expect(normalizeAppPath("/corper/profile/")).toBe("/corper/profile");
  });

  it("falls back to the canonical role path when profile_path is missing", () => {
    expect(normalizeProfilePath("corper")).toBe("/corper/profile");
  });

  it("preserves the corper verification onboarding route", () => {
    expect(normalizeProfilePath("corper", "/corper/verification")).toBe("/corper/verification");
  });

  it("preserves the corper terms onboarding route", () => {
    expect(normalizeProfilePath("corper", "/corper/profile/terms/")).toBe("/corper/profile/terms");
  });


  it("preserves the company terms onboarding route", () => {
    expect(normalizeProfilePath("company", "/company/profile/terms")).toBe("/company/profile/terms");
  });
});

describe("isDiscoveryRouteForRole", () => {
  it("identifies the corper discovery page", () => {
    expect(isDiscoveryRouteForRole("corper", "/corper/companies/")).toBe(true);
  });

  it("identifies the company discovery page", () => {
    expect(isDiscoveryRouteForRole("company", "/company/corpers")).toBe(true);
  });

  it("ignores non-discovery pages", () => {
    expect(isDiscoveryRouteForRole("corper", "/corper/support")).toBe(false);
  });
});

describe("isBillingRouteForRole", () => {
  it("identifies the corper billing page", () => {
    expect(isBillingRouteForRole("corper", "/corper/billing/")).toBe(true);
  });

  it("ignores non-billing pages", () => {
    expect(isBillingRouteForRole("corper", "/corper/profile")).toBe(false);
  });
});
