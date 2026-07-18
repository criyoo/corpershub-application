"use client";

import Image from "next/image";
import Link from "next/link";
import { Building2, Lock, MapPinned } from "lucide-react";

import { BackButton } from "@/components/navigation/back-button";
import { useAuth } from "@/components/providers/auth-provider";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { defaultAppPathForUser } from "@/lib/session";
import { getNigerianStateSlug } from "@/lib/nigerian-reference-data";
import {
  getBillingPathForRole,
  hasPaidCorperAccess,
  type BillingSubscriptionResponse,
} from "@/lib/subscriptions";

type SectorStatsCity = {
  city: string;
  count: number;
};

type SectorStatsState = {
  state: string;
  count: number;
  cities: SectorStatsCity[];
};

type SectorStatsResponse = {
  sector: string;
  total_companies: number;
  states: SectorStatsState[];
};

type SectorDetailClientProps = {
  sector: {
    name: string;
    slug: string;
    imageSrc: string;
  };
};

function pluralizeCompanies(count: number) {
  return count === 1 ? "company" : "companies";
}

export function SectorDetailClient({ sector }: SectorDetailClientProps) {
  const { hydrated, session } = useAuth();
  const stats = useApiQuery<SectorStatsResponse>(
    `/search/company-sector-stats/?sector=${encodeURIComponent(sector.name)}`,
    true,
    60000,
    false
  );
  const subscriptions = useApiQuery<BillingSubscriptionResponse>(
    "/subscriptions/me/",
    hydrated && session?.user.role === "corper",
    60000
  );
  const isCorper = hydrated && session?.user.role === "corper";
  const subscriptionLoading = isCorper && subscriptions.loading && !subscriptions.data;
  const corperHasPaidAccess = hasPaidCorperAccess(subscriptions.data?.results ?? []);
  const isCorperWithoutPaidAccess = isCorper && !subscriptionLoading && !corperHasPaidAccess;
  const visibleStates = stats.data?.states.filter((state) => state.count > 0) ?? [];
  const companyDetailsHref = !session
    ? "/register/corpers"
    : session.user.role === "corper"
      ? isCorperWithoutPaidAccess
        ? getBillingPathForRole("corper")
        : `/corper/sectors/${sector.slug}/companies`
      : defaultAppPathForUser(session.user);
  const getStateCompaniesHref = (stateName: string) =>
    !session
      ? "/register/corpers"
      : session.user.role === "corper"
        ? isCorperWithoutPaidAccess
          ? getBillingPathForRole("corper")
          : `/corper/sectors/${sector.slug}/companies?state=${getNigerianStateSlug(stateName)}`
        : defaultAppPathForUser(session.user);

  return (
    <main className="min-h-screen px-4 pb-16 pt-8 md:px-8 md:pt-12">
      <div className="mx-auto max-w-7xl">
        <BackButton fallbackHref="/sectors" label="Back to sectors" />

        <section className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-stretch">
          <div className="min-w-0">
            <p className="text-sm uppercase tracking-[0.26em] text-lime">Sector</p>
            <h1 className="mt-4 font-display text-4xl text-white md:text-5xl">{sector.name}</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-mist md:text-lg">
              Company coverage by Nigerian state and city for this sector.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <div className="rounded-[24px] border border-white/10 bg-white/[0.07] p-5 shadow-glow">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-lime/15 text-lime">
                    <Building2 className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Registered companies</p>
                    <p className="mt-1 text-3xl font-semibold text-white">
                      {stats.data?.total_companies ?? 0}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-white/10 bg-white/[0.07] p-5 shadow-glow">
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-lime/15 text-lime">
                    <Lock className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">Company details</p>
                    <p className="mt-1 text-sm leading-6 text-white">
                      {isCorperWithoutPaidAccess
                        ? "Paid plan required to view company details."
                        : subscriptionLoading
                          ? "Checking subscription status."
                          : "View matched companies."}
                    </p>
                  </div>
                </div>
                <Link
                  href={subscriptionLoading ? "#" : companyDetailsHref}
                  aria-disabled={subscriptionLoading}
                  className={`mt-5 inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition hover:border-lime/70 hover:bg-white/[0.14] ${subscriptionLoading ? "pointer-events-none opacity-70" : ""
                    }`}
                >
                  {subscriptionLoading ? "Checking..." : "Open"}
                </Link>
              </div>
            </div>
          </div>

          <div className="relative min-h-[280px] overflow-hidden rounded-[28px] border border-white/10 bg-white/[0.07] shadow-glow">
            <Image
              src={sector.imageSrc}
              alt={sector.name}
              fill
              priority
              sizes="(min-width: 1024px) 360px, 100vw"
              className="object-cover"
            />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(7,20,14,0.02)_0%,rgba(7,20,14,0.82)_100%)]" />
          </div>
        </section>

        {stats.error ? (
          <Card className="mt-8 border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to load sector data</h2>
            <p className="mt-3 text-sm text-mist">{stats.error}</p>
          </Card>
        ) : null}

        {!stats.error ? (
          <section className="mt-10">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.26em] text-lime">States and cities</p>
                <h2 className="mt-3 font-display text-3xl text-white">Coverage across Nigeria</h2>
              </div>
              {stats.loading ? <p className="text-sm text-lime">Refreshing counts...</p> : null}
            </div>

            {visibleStates.length ? (
              <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                {visibleStates.map((state) => (
                  <Link
                    key={state.state}
                    href={subscriptionLoading ? "#" : getStateCompaniesHref(state.state)}
                    aria-disabled={subscriptionLoading}
                    className={`group block min-h-[172px] rounded-[24px] border border-white/10 bg-white/[0.07] p-5 shadow-glow transition hover:-translate-y-1 hover:border-lime/40 hover:bg-white/[0.1] ${subscriptionLoading ? "pointer-events-none opacity-70" : ""
                      }`}
                  >
                    <article>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate text-sm font-semibold text-white">{state.state}</h3>
                          <p className="mt-1 text-xl font-bold text-mist">{state.count}</p>
                        </div>
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-lime/15 text-lime transition group-hover:bg-lime/25">
                          <MapPinned className="h-5 w-5" />
                        </span>
                      </div>

                      <div className="mt-5 flex flex-wrap gap-2">
                        {state.cities.length ? (
                          state.cities.map((city) => (
                            <span
                              key={`${state.state}-${city.city}`}
                              className="rounded-full border border-white/10 bg-white/[0.08] px-3 py-1 text-xs text-mist"
                            >
                              {city.city}: {city.count}
                            </span>
                          ))
                        ) : (
                          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-mist">
                            No registered companies yet
                          </span>
                        )}
                      </div>
                    </article>
                  </Link>
                ))}
              </div>
            ) : (
              <Card className="mt-6 text-center">
                <h3 className="font-display text-2xl text-white">No state coverage yet</h3>
                <p className="mt-3 text-sm text-mist">
                  No registered companies have been recorded in this sector yet.
                </p>
              </Card>
            )}
          </section>
        ) : null}
      </div>
    </main>
  );
}
