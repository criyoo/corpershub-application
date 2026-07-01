"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type SVGProps } from "react";

import { CompanyDetailPage } from "@/components/corper/company-detail-page";
import { DirectoryStatsCard } from "@/components/directory/directory-stats-card";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useHomeBackgroundImageUrls } from "@/hooks/use-home-background-image-urls";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCorperCompanyDetailPath } from "@/lib/app-paths";
import { resolveSessionUser } from "@/lib/api";
import {
  // formatCompanyDirectoryLabel,
  getCompanyDirectoryImage,
  getCompanyMonogram,
  type CompanyDirectorySummary,
} from "@/lib/company-directory";
import { defaultAppPathForUser } from "@/lib/session";
import { getBillingPathForRole, isBrowseRestrictionMessage } from "@/lib/subscriptions";

type CompanyResponse = {
  count: number;
  directory_stats: {
    online_count: number;
    active_count: number;
    total_count: number;
  };
  results: CompanyDirectorySummary[];
};

const fallbackPhotoBackgrounds = [
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.12),rgba(9,32,19,0.72)),radial-gradient(circle_at_top,rgba(124,217,161,0.55),transparent_45%),linear-gradient(180deg,#4D7C5D_0%,#173727_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.15),rgba(9,32,19,0.78)),radial-gradient(circle_at_top_left,rgba(255,214,102,0.4),transparent_36%),linear-gradient(180deg,#7D6541_0%,#1D2418_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.12),rgba(9,32,19,0.72)),radial-gradient(circle_at_right,rgba(87,181,231,0.38),transparent_34%),linear-gradient(180deg,#315B68_0%,#12252C_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.15),rgba(9,32,19,0.74)),radial-gradient(circle_at_bottom_left,rgba(241,146,82,0.38),transparent_34%),linear-gradient(180deg,#71473A_0%,#1F1714_100%)]"
];

const SUMMARY_OVERFLOW_SUFFIX = ".......";
let textMeasureContext: CanvasRenderingContext2D | null = null;

function getRecommendationLabel(score: number) {
  if (score >= 75) {
    return "Top match";
  }
  if (score >= 60) {
    return "Strong match";
  }
  if (score >= 30) {
    return "Consider";
  }
  if (score >= 10) {
    return "Very low match";
  }
  return "No Match";
}

function normalizeCompanySummary(value: string) {
  const normalizedValue = value.replace(/\s+/g, " ").trim();
  return normalizedValue || "Company summary not available.";
}

function getTextMeasureContext() {
  if (typeof document === "undefined") {
    return null;
  }

  if (!textMeasureContext) {
    textMeasureContext = document.createElement("canvas").getContext("2d");
  }

  return textMeasureContext;
}

function measureTextWidth(text: string, font: string) {
  const context = getTextMeasureContext();
  if (!context) {
    return text.length * 7;
  }

  context.font = font;
  return context.measureText(text).width;
}

function fitTextToSingleLine(text: string, maxWidth: number, font: string) {
  if (!text || maxWidth <= 0) {
    return text;
  }

  if (measureTextWidth(text, font) <= maxWidth) {
    return text;
  }

  if (measureTextWidth(SUMMARY_OVERFLOW_SUFFIX, font) >= maxWidth) {
    return SUMMARY_OVERFLOW_SUFFIX;
  }

  let low = 0;
  let high = text.length;

  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    const candidate = `${text.slice(0, middle).trimEnd()}${SUMMARY_OVERFLOW_SUFFIX}`;

    if (measureTextWidth(candidate, font) <= maxWidth) {
      low = middle;
    } else {
      high = middle - 1;
    }
  }

  const fittedText = text.slice(0, low).trimEnd();
  if (!fittedText) {
    return SUMMARY_OVERFLOW_SUFFIX;
  }

  const lastSpaceIndex = fittedText.lastIndexOf(" ");
  const safeText =
    lastSpaceIndex > Math.floor(fittedText.length * 0.6)
      ? fittedText.slice(0, lastSpaceIndex).trimEnd()
      : fittedText;

  return `${safeText || fittedText}${SUMMARY_OVERFLOW_SUFFIX}`;
}

function CompanySummaryLine({ summary }: { summary: string }) {
  const summaryRef = useRef<HTMLParagraphElement>(null);
  const [displaySummary, setDisplaySummary] = useState(summary);

  useEffect(() => {
    const element = summaryRef.current;
    if (!element) {
      return;
    }

    const updateSummary = () => {
      const computedStyle = window.getComputedStyle(element);
      const font =
        computedStyle.font ||
        `${computedStyle.fontStyle} ${computedStyle.fontWeight} ${computedStyle.fontSize} ${computedStyle.fontFamily}`;

      setDisplaySummary(fitTextToSingleLine(summary, element.clientWidth, font));
    };

    updateSummary();

    const resizeObserver = new ResizeObserver(() => updateSummary());
    resizeObserver.observe(element);

    return () => resizeObserver.disconnect();
  }, [summary]);

  return (
    <p ref={summaryRef} className="mt-2 overflow-hidden whitespace-nowrap text-[12px] leading-4 text-white/80">
      {displaySummary}
    </p>
  );
}

function SearchIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  );
}

function LocationIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 21s6-5.4 6-11a6 6 0 1 0-12 0c0 5.6 6 11 6 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}

function CompanyCardSkeleton({ index }: { index: number; key?: React.Key }) {
  return (
    <div className="aspect-square overflow-hidden rounded-[32px] border border-white/10 bg-white/[0.08]">
      <div
        className={`h-[75%] animate-pulse ${fallbackPhotoBackgrounds[index % fallbackPhotoBackgrounds.length]
          }`}
      />
      <div className="flex h-[25%] flex-col justify-end gap-2 p-4">
        <div className="h-3 w-40 animate-pulse rounded-full bg-white/12" />
        <div className="h-3 w-28 animate-pulse rounded-full bg-white/12" />
        <div className="h-10 animate-pulse rounded-[18px] bg-white/12" />
      </div>
    </div>
  );
}

export function DiscoverCompaniesPage({
  imageUrls = [],
  publicBrowse = false,
}: {
  imageUrls?: string[];
  publicBrowse?: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hydrated, session, updateSession } = useAuth();
  const backgroundImageUrls = useHomeBackgroundImageUrls(imageUrls);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const selectedCompanyId = searchParams.get("companyId");

  const isCorper = hydrated && session?.user.role === "corper";
  const companies = useApiQuery<CompanyResponse>(
    `/search/companies/?search=${encodeURIComponent(searchQuery)}`,
    publicBrowse || isCorper,
    60000
  );
  const isGuestViewer = publicBrowse && !session;
  const isInteractiveCard = publicBrowse ? hydrated : isCorper;
  const visibleNowCard = (
    <DirectoryStatsCard
      title="Companies Stats"
      items={[
        {
          label: "Companies online",
          value: companies.data?.directory_stats.online_count ?? 0,
        },
        {
          label: "Active Companies",
          value: companies.data?.directory_stats.active_count ?? 0,
        },
        {
          label: "Total Companies",
          value: companies.data?.directory_stats.total_count ?? 0,
        },
      ]}
    />
  );

  useEffect(() => {
    if (publicBrowse) {
      return;
    }

    if (!hydrated) {
      return;
    }

    if (!session) {
      router.replace("/login/");
      return;
    }

    if (session.user.role !== "corper") {
      router.replace(defaultAppPathForUser(session.user));
    }
  }, [hydrated, publicBrowse, router, session]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextQuery = searchInput.trim();
    if (nextQuery === searchQuery) {
      void companies.refetch();
      return;
    }

    setSearchQuery(nextQuery);
  }

  function clearSearch() {
    setSearchInput("");
    setSearchQuery("");
  }

  async function openCompanyDetails(companyId: string) {
    if (!hydrated) {
      return;
    }

    if (!session) {
      router.push("/register/corpers");
      return;
    }

    let activeUser = session.user;

    try {
      const resolvedUser = await resolveSessionUser();
      if (!resolvedUser) {
        updateSession(null);
        router.push("/register/corpers");
        return;
      }

      activeUser = resolvedUser;
      updateSession({
        ...session,
        user: resolvedUser
      });
    } catch {
      activeUser = session.user;
    }

    if (activeUser.role === "corper") {
      router.push(buildCorperCompanyDetailPath(companyId));
      return;
    }

    router.push(defaultAppPathForUser(activeUser));
  }
  if (!publicBrowse && (!hydrated || !session || session.user.role !== "corper")) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-full border border-white/10 bg-white/[0.08] px-5 py-3 text-sm text-mist backdrop-blur-xl">
          Loading company directory...
        </div>
      </main>
    );
  }

  if (selectedCompanyId) {
    return <CompanyDetailPage companyId={selectedCompanyId} imageUrls={backgroundImageUrls} />;
  }

  function handleCardKeyDown(event: React.KeyboardEvent<HTMLElement>, companyId: string) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    void openCompanyDetails(companyId);
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto min-h-screen max-w-[1680px] px-4 py-2 md:px-8 md:py-3 lg:px-10">
        {!publicBrowse ? (
          <Link
            href="/corper/dashboard"
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </Link>
        ) : null}

        <section className={`${publicBrowse ? "mt-8" : "mt-10"} rounded-[34px] border border-white/10 bg-white/[0.07] px-4 py-3 shadow-glow backdrop-blur-xl md:px-7 lg:px-8`}>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <p className="pt-1 text-xs uppercase tracking-[0.26em] text-lime">Discover companies</p>
            {visibleNowCard}
          </div>

          <div className="mx-auto mt-5 max-w-3xl text-center">
            <h1 className="font-display text-4xl text-white md:text-5xl">Browse Companies</h1>
          </div>
          <div className="mx-auto mt-3 max-w-3xl text-center">
            <p className="max-w-3xl text-base">
              {searchQuery
                ? `Showing ${companies.data?.count ?? 0} result${companies.data?.count === 1 ? "" : "s"} for "${searchQuery}".`
                : isGuestViewer
                  ? "Search by name, sector, state, city, or function to find companies that fit your service needs."
                  : "Verified companies ranked by how well they fit your profile. Open a company to express interest."}
            </p>
          </div>

          <form
            onSubmit={handleSearchSubmit}
            className="relative z-10 mx-auto mt-8 flex w-full max-w-[880px] flex-col gap-3 rounded-[32px] border border-white/12 bg-white px-3 py-1 shadow-[0_30px_80px_rgba(4,21,15,0.22)] md:flex-row md:items-center"
          >
            <div
              className="relative z-10 flex min-w-0 flex-1 items-center gap-3 rounded-[24px] bg-[#F3F7F4] px-4 py-4"
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#DCECE2] text-[#134B35]">
                <SearchIcon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#436B56]">Search companies</p>
                <input
                  autoComplete="off"
                  className="mt-1 w-full border-0 bg-transparent p-0 text-base text-[#0C2E21] placeholder:text-[grey] focus:outline-none"
                  name="company_search"
                  onChange={(event) => setSearchInput(event.target.value)}
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => event.stopPropagation()}
                  placeholder='Search companies by name, state, sector, company type, etc'
                  spellCheck={false}
                  type="text"
                  value={searchInput}
                />
              </div>
            </div>

            {searchQuery ? (
              <button
                type="button"
                onClick={clearSearch}
                className="rounded-[24px] px-5 py-4 text-sm font-semibold text-[#0C2E21] transition hover:bg-[#EEF5F1]"
              >
                Clear
              </button>
            ) : null}

            <Button type="submit" className="h-[68px] rounded-[24px] px-8 text-base">
              Search
            </Button>
          </form>

          <div className="mt-5 flex flex-col items-center gap-2 text-center text-sm text-mist">
            {companies.loading && companies.data ? <p className="text-lime">Refreshing results...</p> : null}
          </div>
        </section>

        {companies.error ? (
          <Card className="mt-6 border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to load companies</h2>
            <p className="mt-3 text-sm text-mist">{companies.error}</p>
            {isBrowseRestrictionMessage(companies.error) ? (
              <Link
                href={getBillingPathForRole("corper")}
                className="mt-5 inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                Open billing
              </Link>
            ) : null}
          </Card>
        ) : null}

        {!companies.error && companies.loading && !companies.data ? (
          <section className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <CompanyCardSkeleton key={index} index={index} />
            ))}
          </section>
        ) : null}

        {!companies.error && !companies.loading && companies.data?.results.length === 0 ? (
          <Card className="mt-6 text-center">
            <h2 className="font-display text-2xl text-white">No companies found</h2>
            <p className="mt-3 text-sm text-mist">
              Try a different keyword or clear the search to return to the full directory.
            </p>
          </Card>
        ) : null}

        {!companies.error && companies.data?.results.length ? (
          <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {companies.data.results.map((company, index) => {
              const imageUrl = getCompanyDirectoryImage(backgroundImageUrls, company.id, company.company_image);
              const matchScore = company.match_score;
              const canShowRecommendation = matchScore !== null;
              const recommendationLabel = canShowRecommendation
                ? getRecommendationLabel(matchScore)
                : "";
              const companySummary = normalizeCompanySummary(company.summary_description);
              // const recommendationReason = company.match_reasons[0] ?? "";

              return (
                <article
                  key={company.id}
                  className={`group flex aspect-square flex-col overflow-hidden rounded-[32px] border border-white/10 bg-white/[0.08] shadow-glow backdrop-blur-xl transition duration-300 ${isInteractiveCard ? "cursor-pointer hover:-translate-y-1 hover:border-lime/35" : ""
                    }`}
                  onClick={isInteractiveCard ? () => void openCompanyDetails(company.id) : undefined}
                  onKeyDown={isInteractiveCard ? (event) => handleCardKeyDown(event, company.id) : undefined}
                  role={isInteractiveCard ? "link" : undefined}
                  tabIndex={isInteractiveCard ? 0 : undefined}
                >
                  <div className="relative h-[75%] overflow-hidden">
                    {imageUrl ? (
                      <Image
                        alt=""
                        aria-hidden="true"
                        className="object-cover transition duration-500 group-hover:scale-150"
                        fill
                        sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                        src={imageUrl}
                        unoptimized
                      />
                    ) : (
                      <div
                        className={`h-full w-full ${fallbackPhotoBackgrounds[index % fallbackPhotoBackgrounds.length]
                          }`}
                      />
                    )}

                    <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(7,20,14,0.08)_0%,rgba(7,20,14,0.18)_35%,rgba(7,20,14,0.88)_100%)]" />
                    <div className="absolute right-4 top-4 flex items-center gap-2">
                      {canShowRecommendation && recommendationLabel ? (
                        <div className="rounded-full border border-lime/40 bg-yellow-500 px-3 py-1 text-[10px] uppercase tracking-[0.10em] text-green-900 backdrop-blur-sm">
                          <b>{recommendationLabel}</b> . <b>{matchScore}%</b>
                        </div>
                      ) : null}
                    </div>
                    <div className="absolute inset-x-4 bottom-4 flex items-end gap-3">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[20px] border border-white/12 bg-white/10 text-lg font-semibold text-white backdrop-blur-md">
                        {getCompanyMonogram(company.company_name)}
                      </div>
                      <div className="min-w-0">
                        <h2 className="truncate font-display text-[16px] text-white"><b>{company.company_name}</b></h2>
                        <p className="truncate text-xs text-white/78">{company.company_sector}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex min-h-0 flex-1 flex-col justify-end p-3">
                    <p className="truncate text-[12px] font-semibold uppercase tracking-[0.10em] text-white/100 text-lime">
                      {company.company_function || "Function not specified"}
                    </p>
                    <CompanySummaryLine summary={companySummary} />
                    <div className="mt-2 flex min-w-0 items-center gap-2 text-[12px] text-mist">
                      <LocationIcon className="h-5 w-5 shrink-0 text-lime" />
                      <span className="min-w-0 truncate text-[12px] text-lime">{company.location}</span>
                    </div>
                  </div>
                </article>
              );
            })}
          </section>
        ) : null}
      </div>
    </main>
  );
}
