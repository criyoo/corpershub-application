"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { SignOutButton } from "@/components/layout/sign-out-button";
import { useAuth } from "@/components/providers/auth-provider";
import { useApiQuery } from "@/hooks/use-api-query";
import { dashboardNav } from "@/lib/nav";
import {
  defaultAppPathForUser,
  isBillingRouteForRole,
  isDiscoveryRouteForRole,
  loginPathForRole,
  normalizeAppPath,
  type UserRole,
} from "@/lib/session";

type CorperStatusSummary = {
  full_name?: string;
  verification_status: string;
  is_complete: boolean;
  profile_fields_complete: boolean;
  terms_accepted: boolean;
  biodata_verification_status: string;
  nin_verification_status: string;
  nysc_callup_verification_status: string;
  nysc_state_code_verification_status: string;
};

type CompanyStatusSummary = {
  company_name?: string;
  is_complete: boolean;
  verification_status?: string;
  approval_status?: string;
  verification_fields_complete: boolean;
  profile_fields_complete: boolean;
  terms_accepted: boolean;
};

function getCompanyShortName(companyName?: string) {
  const normalizedName = companyName?.trim();
  if (!normalizedName) {
    return "Company";
  }
  return normalizedName.split(/\s+/)[0] || "Company";
}

function resolveCorperOnboardingPath(profile: CorperStatusSummary) {
  const documentsVerified =
    profile.biodata_verification_status === "verified" &&
    profile.nin_verification_status === "verified" &&
    profile.nysc_callup_verification_status === "verified" &&
    profile.nysc_state_code_verification_status === "verified";

  if (!documentsVerified) {
    return "/corper/verification";
  }

  if (!profile.terms_accepted) {
    return "/corper/profile/terms";
  }

  if (!profile.is_complete) {
    return "/corper/profile";
  }

  return null;
}

function resolveCompanyOnboardingPath(profile: CompanyStatusSummary) {
  if (
    !profile.verification_fields_complete ||
    (profile.terms_accepted && profile.verification_status !== "verified")
  ) {
    return "/company/verification";
  }

  if (!profile.terms_accepted) {
    return "/company/profile/terms";
  }

  if (!profile.profile_fields_complete || !profile.is_complete) {
    return "/company/profile";
  }

  return null;
}

export function DashboardShell({
  role,
  title,
  headerLabel = "Corpershub",
  sidebarBelowBrand,
  titleBadge,
  headerActions,
  headerAside,
  hideDefaultHeaderAside = false,
  hideCorperBanner = false,
  hideBanner = false,
  children
}: {
  role: UserRole;
  title: string;
  headerLabel?: React.ReactNode;
  sidebarBelowBrand?: React.ReactNode;
  titleBadge?: React.ReactNode;
  headerActions?: React.ReactNode;
  headerAside?: React.ReactNode;
  hideDefaultHeaderAside?: boolean;
  hideCorperBanner?: boolean;
  hideBanner?: boolean;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const normalizedPathname = normalizeAppPath(pathname ?? "/");
  const isBillingRoute = isBillingRouteForRole(role, normalizedPathname);
  const isDiscoveryRoute = isDiscoveryRouteForRole(role, normalizedPathname);
  const isCorperTermsPath = normalizedPathname.startsWith("/corper/profile/terms");
  const isCompanyTermsPath = normalizedPathname.startsWith("/company/profile/terms");
  const router = useRouter();
  const { hydrated, session, updateSession, inactivityWarning, extendSession } = useAuth();
  const corperProfile = useApiQuery<CorperStatusSummary>(
    "/corpers/me/",
    hydrated && Boolean(session) && role === "corper" && session?.user.role === "corper",
    10000
  );
  const companyProfile = useApiQuery<CompanyStatusSummary>(
    "/companies/me/",
    hydrated && Boolean(session) && role === "company" && session?.user.role === "company",
    10000
  );
  const resolvedProfileCompleted =
    role === "corper"
      ? (corperProfile.data?.is_complete ?? session?.user.profile_completed)
      : role === "company"
        ? (companyProfile.data?.is_complete ?? session?.user.profile_completed)
        : session?.user.profile_completed;
  const corperVerificationStatus = role === "corper" ? corperProfile.data?.verification_status ?? null : null;
  const corperDocumentsVerified =
    role === "corper"
      ? corperProfile.data?.biodata_verification_status === "verified" &&
      corperProfile.data?.nin_verification_status === "verified" &&
      corperProfile.data?.nysc_callup_verification_status === "verified" &&
      corperProfile.data?.nysc_state_code_verification_status === "verified"
      : true;
  const corperFirstName = corperProfile.data?.full_name?.trim().split(/\s+/)[0] ?? "";
  const shouldShowAutoCorperWelcome =
    role === "corper" && Boolean(corperFirstName) && !normalizedPathname.startsWith("/corper/companies");
  const shouldShowAutoCompanyWelcome = role === "company" && normalizedPathname === "/company/dashboard";
  const companyShortName = getCompanyShortName(companyProfile.data?.company_name);
  const resolvedSidebarBelowBrand =
    sidebarBelowBrand ??
    (shouldShowAutoCorperWelcome ? (
      <p className="font-display text-2xl text-white">Welcome back <b />{corperFirstName}</p>
    ) : shouldShowAutoCompanyWelcome ? (
      <p className="font-display text-2xl text-white">
        Welcome to<b />{companyShortName} Dashboard
      </p>
    ) : null);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    if (!session) {
      router.replace(`${loginPathForRole(role)}?next=${encodeURIComponent(normalizedPathname)}`);
      return;
    }
    if (session.user.role !== role) {
      router.replace(defaultAppPathForUser(session.user));
      return;
    }
    if (role === "corper" && corperProfile.loading && !corperProfile.data) {
      return;
    }

    if (role === "corper" && corperProfile.data) {
      const requiredPath = resolveCorperOnboardingPath(corperProfile.data);
      if (
        requiredPath === "/corper/verification" &&
        normalizedPathname !== requiredPath &&
        !isCorperTermsPath
      ) {
        router.replace(requiredPath);
        return;
      }
      if (
        requiredPath &&
        requiredPath !== "/corper/verification" &&
        (isBillingRoute || isDiscoveryRoute)
      ) {
        router.replace(requiredPath);
        return;
      }

      if (!requiredPath && session.user.needs_subscription_selection && isDiscoveryRoute) {
        router.replace("/corper/billing");
        return;
      }
    }
    if (role === "company" && companyProfile.data) {
      const requiredPath = resolveCompanyOnboardingPath(companyProfile.data);
      if (requiredPath && isDiscoveryRoute) {
        router.replace(requiredPath);
        return;
      }
    }
  }, [
    companyProfile.data,
    corperProfile.data,
    corperProfile.loading,
    hydrated,
    isCompanyTermsPath,
    isCorperTermsPath,
    normalizedPathname,
    resolvedProfileCompleted,
    role,
    router,
    session,
  ]);

  useEffect(() => {
    if (
      !session ||
      role !== "company" ||
      session.user.role !== "company" ||
      !companyProfile.data ||
      (session.user.profile_completed === companyProfile.data.is_complete &&
        session.user.profile_path === (resolveCompanyOnboardingPath(companyProfile.data) ?? "/company/corpers") &&
        session.user.company_verification_status === (companyProfile.data.verification_status ?? null))
    ) {
      return;
    }

    updateSession({
      ...session,
      user: {
        ...session.user,
        profile_completed: companyProfile.data.is_complete,
        profile_path: resolveCompanyOnboardingPath(companyProfile.data) ?? "/company/corpers",
        company_verification_status: companyProfile.data.verification_status ?? null,
      },
    });
  }, [companyProfile.data, role, session, updateSession]);

  useEffect(() => {
    if (!session || role !== "corper" || session.user.role !== "corper" || !corperProfile.data) {
      return;
    }

    const documentsVerified =
      corperProfile.data.biodata_verification_status === "verified" &&
      corperProfile.data.nin_verification_status === "verified" &&
      corperProfile.data.nysc_callup_verification_status === "verified" &&
      corperProfile.data.nysc_state_code_verification_status === "verified";
    const profileCompleted = documentsVerified && corperProfile.data.is_complete;
    const profilePath =
      !corperProfile.data.terms_accepted && isCorperTermsPath
        ? "/corper/profile/terms"
        : resolveCorperOnboardingPath(corperProfile.data) ?? "/corper/profile";

    if (
      session.user.profile_completed === profileCompleted &&
      session.user.profile_path === profilePath
    ) {
      return;
    }

    updateSession({
      ...session,
      user: {
        ...session.user,
        profile_completed: profileCompleted,
        profile_path: profilePath,
      },
    });
  }, [corperProfile.data, isCorperTermsPath, role, session, updateSession]);

  useEffect(() => {
    if (role !== "corper") {
      return;
    }

    function handleCorperProfileUpdated() {
      void corperProfile.refetch();
    }

    window.addEventListener("corper-profile-updated", handleCorperProfileUpdated);
    return () => window.removeEventListener("corper-profile-updated", handleCorperProfileUpdated);
  }, [role, corperProfile]);

  useEffect(() => {
    if (!hydrated || !session || session.user.role !== role) {
      return;
    }

    let cancelled = false;
    const routeQueue = dashboardNav[role]
      .map((item) => item.href)
      .filter((href) => href !== normalizedPathname);
    const fallbackTimerIds: Array<ReturnType<typeof globalThis.setTimeout>> = [];

    const prefetchRoutes = () => {
      routeQueue.forEach((href, index) => {
        const timerId = globalThis.setTimeout(() => {
          if (!cancelled) {
            void router.prefetch(href);
          }
        }, index * 120);
        fallbackTimerIds.push(timerId);
      });
    };

    if ("requestIdleCallback" in window) {
      const idleCallbackId = window.requestIdleCallback(prefetchRoutes, { timeout: 1500 });
      return () => {
        cancelled = true;
        window.cancelIdleCallback(idleCallbackId);
        fallbackTimerIds.forEach((timerId) => globalThis.clearTimeout(timerId));
      };
    }

    const timerId = globalThis.setTimeout(prefetchRoutes, 250);
    fallbackTimerIds.push(timerId);

    return () => {
      cancelled = true;
      fallbackTimerIds.forEach((activeTimerId) => globalThis.clearTimeout(activeTimerId));
    };
  }, [hydrated, normalizedPathname, role, router, session]);

  const corperBanner =
    role === "corper" && !hideCorperBanner
      ? !corperDocumentsVerified
        ? {
          className: "border-[#BEE3CA] bg-[linear-gradient(135deg,rgba(31,183,102,0.18),rgba(236,248,240,0.12))] text-white",
          message: "Some verification information are missing, Complete all fields to unlock profile editing.",
        }
        : corperVerificationStatus === "under_review"
          ? {
            className: "border-[#BBF7D0] bg-[linear-gradient(135deg,rgba(56,189,248,0.18),rgba(220,252,231,0.12))] text-white",
            message: "Profile verification submitted successfully",
          }
          : corperVerificationStatus === "rejected"
            ? {
              className: "border-[#FECACA] bg-[linear-gradient(135deg,rgba(239,68,68,0.16),rgba(254,242,242,0.1))] text-white",
              message: "Profile verification requires attention",
            }
            : null
      : resolvedProfileCompleted === false
        ? {
          className: "border-[#BEE3CA] bg-[linear-gradient(135deg,rgba(31,183,102,0.18),rgba(236,248,240,0.12))] text-white",
          message: `Complete verification to continue using the platform.`,
        }
        : null;
  const navLinks: React.ReactNode[] = [];
  let activeSection: string | undefined;

  for (const item of dashboardNav[role]) {
    if (item.section && item.section !== activeSection) {
      activeSection = item.section;
      navLinks.push(
        <p
          key={`section-${role}-${item.section}`}
          className="mt-4 px-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-lime/80 first:mt-0"
        >
          {item.section}
        </p>
      );
    }

    navLinks.push(
      <Link
        key={item.href}
        href={item.href}
        onMouseEnter={() => void router.prefetch(item.href)}
        onFocus={() => void router.prefetch(item.href)}
        className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition ${normalizedPathname === item.href ? "bg-white text-ink shadow-[0_12px_30px_rgba(4,21,15,0.15)]" : "text-mist hover:bg-white/[0.08] hover:text-white"
          }`}
      >
        {item.icon ? <item.icon className="h-5 w-5 shrink-0" /> : null}
        <span>{item.label}</span>
      </Link>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(124,217,161,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,255,255,0.1),_transparent_18%),linear-gradient(180deg,_#134B35_0%,_#0B261B_58%,_#07140E_100%)]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col gap-6 px-4 py-4 lg:flex-row lg:px-6">
        <aside className="flex w-full flex-col rounded-[32px] border border-white/10 bg-white/[0.08] p-5 backdrop-blur-xl lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)] lg:w-72">
          <div className="flex flex-col items-center">
            <Link
              href="/"
              className="inline-flex items-center justify-center rounded-full border border-lime/80 bg-lime/10 px-6 py-2.5 font-display text-xl font-bold text-[#E6D28C] shadow-[0_0_0_1px_rgba(194,255,119,0.08),0_14px_30px_rgba(7,20,14,0.18)] transition hover:bg-lime hover:text-[#E6D28C] hover:shadow-[0_18px_34px_rgba(194,255,119,0.24)]"
            >
              Corpershub
            </Link>
            {resolvedSidebarBelowBrand ? <div className="mt-4 text-center">{resolvedSidebarBelowBrand}</div> : null}
          </div>
          <nav className="mt-24 grid gap-2">{navLinks}</nav>
          <div className="mt-auto flex justify-center pt-8">
            <SignOutButton className="min-w-36 justify-center" variant="secondary" />
          </div>
        </aside>
        <main className="flex-1 rounded-[32px] border border-white/10 bg-white/[0.06] p-6 shadow-glow backdrop-blur-xl">
          <div className="mb-8 flex flex-col gap-3 border-b border-white/10 pb-6 md:flex-row md:items-end md:justify-between">
            <div>
              {headerActions ? <div className="mb-4">{headerActions}</div> : null}
              {headerLabel ? <p className="text-xs uppercase tracking-[0.24em] text-lime">{headerLabel}</p> : null}
            {title ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h1 className="font-display text-3xl text-white">{title}</h1>
                {titleBadge ? <div>{titleBadge}</div> : null}
              </div>
            ) : titleBadge ? (
              <div>{titleBadge}</div>
            ) : null}
            </div>
            {headerAside !== undefined ? (
              <div>{headerAside}</div>
            ) : hideDefaultHeaderAside || role !== "admin" ? null : (
              <div className="text-sm text-mist">{session?.user.email}</div>
            )}
          </div>
{corperBanner && !hideBanner ? (
             <div className={`mb-6 rounded-[24px] border px-5 py-4 text-sm ${corperBanner.className}`}>
               {corperBanner.message}
             </div>
           ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}
