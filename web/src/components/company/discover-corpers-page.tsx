"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { type FormEvent, type SVGProps, useEffect, useState } from "react";

import { DirectoryStatsCard } from "@/components/directory/directory-stats-card";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CorperDetailPage } from "@/components/company/corper-detail-page";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCompanyCorperDetailPath } from "@/lib/app-paths";
import { resolveMediaUrl } from "@/lib/media";
import { defaultAppPathForUser } from "@/lib/session";

type CorperCard = {
  id: string;
  full_name: string;
  field_of_study: string;
  degree: string;
  university: string;
  graduation_year: number | null;
  profile_photo: string | null;
  skill: string;
  posting_location_state: string;
  verification_status: string;
  is_online: boolean;
  match_score: number | null;
  match_reasons: string[];
  recommended: boolean;
};

type CorperResponse = {
  count: number;
  directory_stats: {
    online_count: number;
    active_count: number;
    total_count: number;
  };
  results: CorperCard[];
};

const photoCardFallbacks = [
  "bg-[radial-gradient(circle_at_top,_rgba(124,217,161,0.92),rgba(19,75,53,0.96))]",
  "bg-[radial-gradient(circle_at_top_left,_rgba(255,214,102,0.88),rgba(125,101,65,0.96))]",
  "bg-[radial-gradient(circle_at_right,_rgba(87,181,231,0.82),rgba(49,91,104,0.96))]",
  "bg-[radial-gradient(circle_at_bottom_left,_rgba(241,146,82,0.82),rgba(113,71,58,0.96))]",
];

const corperCardBackground =
  "bg-[radial-gradient(circle_at_top,_rgba(124,217,161,0.24),transparent_42%),linear-gradient(180deg,#1A523B_0%,#103222_58%,#0A1E15_100%)]";

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

function StudyIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M3 7.5 12 4l9 3.5-9 3.5L3 7.5Z" />
      <path d="M7 10.5v4c0 1.9 2.2 3.5 5 3.5s5-1.6 5-3.5v-4" />
    </svg>
  );
}

function SkillIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3 4 7v5c0 5.2 3.4 8.8 8 10 4.6-1.2 8-4.8 8-10V7l-8-4Z" />
      <path d="M9 12h6" />
      <path d="M12 9v6" />
    </svg>
  );
}

function CorperCardSkeleton({ index }: { index: number; key?: React.Key }) {
  return (
    <div className={`overflow-hidden rounded-[32px] shadow-[0_18px_50px_rgba(5,20,14,0.28)] ${corperCardBackground}`}>
      <div className="relative h-[460px] animate-pulse overflow-hidden">
        <div className={`relative h-[368px] border-b border-white/10 ${photoCardFallbacks[index % photoCardFallbacks.length]}`}>
          <div className="absolute right-4 top-4 h-7 w-24 rounded-full border border-white/15 bg-white/20" />
          <div className="absolute inset-x-0 bottom-0 px-4 pb-4 pt-20">
            <div className="h-6 w-40 rounded-full bg-white/20" />
            <div className="mt-3 h-4 w-28 rounded-full bg-white/20" />
          </div>
        </div>
        <div className="grid h-[92px] gap-2 px-4 py-3">
          <div className="h-9 rounded-[18px] bg-white/12" />
          <div className="h-9 rounded-[18px] bg-white/12" />
        </div>
      </div>
    </div>
  );
}

function getInitials(name: string) {
  const parts = name
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "C";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

function formatStatusLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

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

export function DiscoverCorpersPage({ publicBrowse = false }: { publicBrowse?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hydrated, session } = useAuth();
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const selectedCorperId = searchParams.get("corperId");

  const isCompany = hydrated && session?.user.role === "company";
  const corpers = useApiQuery<CorperResponse>(
    `/search/corpers/?search=${encodeURIComponent(searchQuery)}`,
    publicBrowse || isCompany,
    60000
  );
  const isGuestViewer = publicBrowse && !session;
  const visibleNowCard = (
    <DirectoryStatsCard
      title="Corpers Stats"
      items={[
        {
          label: "Corpers online",
          value: corpers.data?.directory_stats.online_count ?? 0,
        },
        {
          label: "Active Corpers",
          value: corpers.data?.directory_stats.active_count ?? 0,
        },
        {
          label: "Total Corpers",
          value: corpers.data?.directory_stats.total_count ?? 0,
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

    if (session.user.role !== "company") {
      router.replace(defaultAppPathForUser(session.user));
    }
  }, [hydrated, publicBrowse, router, session]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextQuery = searchInput.trim();
    if (nextQuery === searchQuery) {
      void corpers.refetch();
      return;
    }

    setSearchQuery(nextQuery);
  }

  function clearSearch() {
    setSearchInput("");
    setSearchQuery("");
  }

  function openCorperDetails(corperId: string) {
    if (!session) {
      router.push("/register/companies");
      return;
    }

    if (session.user.role === "company") {
      router.push(buildCompanyCorperDetailPath(corperId));
      return;
    }

    router.push(defaultAppPathForUser(session.user));
  }

  function handleCardKeyDown(event: React.KeyboardEvent<HTMLElement>, corperId: string) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    openCorperDetails(corperId);
  }

  if (!publicBrowse && (!hydrated || !session || session.user.role !== "company")) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-full border border-white/10 bg-white/[0.08] px-5 py-3 text-sm text-mist backdrop-blur-xl">
          Loading corper directory...
        </div>
      </main>
    );
  }

  if (selectedCorperId) {
    return (
      <CorperDetailPage
        corperId={selectedCorperId}
        onBackToDirectory={() => router.replace("/company/corpers")}
      />
    );
  }

  return (
    <main className="min-h-screen">
      <div className="mx-auto min-h-screen max-w-[1680px] px-4 py-2 md:px-8 md:py-3 lg:px-10">
        {!publicBrowse ? (
          <Link
            href="/company/dashboard"
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </Link>
        ) : null}

        <section className={`${publicBrowse ? "mt-8" : "mt-10"} rounded-[34px] border border-white/10 bg-white/[0.07] px-3 py-3 shadow-glow backdrop-blur-xl md:px-4 lg:px-8`}>
          {publicBrowse ? (
            <>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <p className="text-xs uppercase tracking-[0.26em] text-lime">Discover corpers</p>
                {visibleNowCard}
              </div>

              <div className="mx-auto mt-6 max-w-3xl text-center">
                <h1 className="font-display text-4xl text-white md:text-5xl">Browse verified corpers.</h1>
                <p className="mx-auto mt-3 max-w-2xl text-xs">
                  Search by age, university, posting state, course, graduation year, skills, or gender to find corpers that fit your needs.
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <p className="text-xs uppercase tracking-[0.26em] text-lime">Discover corpers</p>
                {visibleNowCard}
              </div>

              <div className="mx-auto mt-6 max-w-3xl text-center">
                <h1 className="font-display text-4xl text-white md:text-5xl">Search verified corpers.</h1>
                <p className="mx-auto mt-3 max-w-2xl text-xs">
                  Search by age, university, posting state, course, graduation year, skills, or gender to find corpers that fit your needs.
                </p>
              </div>
            </>
          )}

          <form
            onSubmit={handleSearchSubmit}
            className={`relative z-10 mx-auto flex w-full max-w-[880px] flex-col gap-3 rounded-[32px] border border-white/12 bg-white px-3 py-1 shadow-[0_30px_80px_rgba(4,21,15,0.22)] md:flex-row md:items-center ${publicBrowse ? "mt-6" : "mt-8"
              }`}
          >
            <div
              className="relative z-10 flex min-w-0 flex-1 items-center gap-3 rounded-[24px] bg-[#F3F7F4] px-4 py-3"
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#DCECE2] text-[#134B35]">
                <SearchIcon className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-semibold uppercase tracking-[0.10em] text-[#436B56]">Search corpers</p>
                <input
                  autoComplete="off"
                  className="mt-1 w-full border-0 bg-transparent p-0 text-[12px] text-[#0C2E21] placeholder:text-[grey] focus:outline-none"
                  name="corper_search"
                  onChange={(event) => setSearchInput(event.target.value)}
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => event.stopPropagation()}
                  placeholder='Search corp members by posting state, univeristy, qualification, gender, age range e.g "19-26" etc"'
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
                className="rounded-[24px] px-5 py-3 text-sm font-semibold text-[#0C2E21] transition hover:bg-[#EEF5F1]"
              >
                Clear
              </button>
            ) : null}

            <Button type="submit" className="h-[60px] rounded-[24px] px-8 text-base">
              Search
            </Button>
          </form>

          <div className="mt-5 flex flex-col gap-2 text-sm text-mist md:flex-row md:items-center md:justify-between">
            {corpers.loading && corpers.data ? <p className="text-lime">Refreshing results...</p> : null}
          </div>
        </section>

        {corpers.error ? (
          <Card className="mt-6 border-coral/30 bg-coral/10">
            <h2 className="font-display text-2xl text-white">Unable to load corpers</h2>
            <p className="mt-3 text-sm text-mist">{corpers.error}</p>
          </Card>
        ) : null}

        {!corpers.error && corpers.loading && !corpers.data ? (
          <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <CorperCardSkeleton key={index} index={index} />
            ))}
          </section>
        ) : null}

        {!corpers.error && !corpers.loading && corpers.data?.results.length === 0 ? (
          <Card className="mt-6 text-center">
            <h2 className="font-display text-2xl text-white">No corpers found</h2>
            <p className="mt-3 text-sm text-mist">
              Try a different keyword or clear the search to return to the full directory.
            </p>
          </Card>
        ) : null}

        {!corpers.error && corpers.data?.results.length ? (
          <section className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {corpers.data.results.map((corper, index) => {
              const photoUrl =
                corper.verification_status === "verified" && corper.profile_photo
                  ? resolveMediaUrl(corper.profile_photo)
                  : null;
              const qualification = [corper.degree, corper.field_of_study].filter(Boolean).join(" · ");
              const universityName = corper.university || "University not specified";
              const matchScore = corper.match_score;
              const canShowRecommendation = matchScore !== null;
              const recommendationLabel = canShowRecommendation
                ? getRecommendationLabel(matchScore)
                : "";
              const recommendationReason = corper.match_reasons[0] ?? "";

              return (
                <article
                  key={corper.id}
                  className={`group h-[460px] cursor-pointer overflow-hidden rounded-[32px] text-white shadow-[0_18px_50px_rgba(5,20,14,0.28)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_26px_70px_rgba(5,20,14,0.34)] ${corperCardBackground}`}
                  onClick={() => openCorperDetails(corper.id)}
                  onKeyDown={(event) => handleCardKeyDown(event, corper.id)}
                  role="link"
                  tabIndex={0}
                >
                  <div className="flex h-full flex-col">
                    <div className="relative h-[368px] overflow-hidden border-b border-white/10">
                      <div className="absolute inset-0">
                        {photoUrl ? (
                          <img
                            src={photoUrl}
                            alt={corper.full_name}
                            className="h-full w-full object-cover object-[center_10%] transition duration-500 group-hover:scale-[1.50]"
                          />
                        ) : (
                          <div
                            className={`flex h-full w-full items-center justify-center text-7xl font-semibold text-white ${photoCardFallbacks[index % photoCardFallbacks.length]
                              }`}
                          >
                            {getInitials(corper.full_name)}
                          </div>
                        )}
                      </div>

                      <div className="absolute inset-0 bg-gradient-to-b from-[#07140E]/8 via-[#07140E]/16 to-[#07140E]/92" />

                      <div className="absolute left-4 top-4">
                        {canShowRecommendation ? (
                          <div className="inline-flex items-center rounded-full border border-lime/40 bg-[#07140E]/70 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-lime backdrop-blur-sm">
                            {recommendationLabel} . {matchScore}%
                          </div>
                        ) : null}
                      </div>

                      <div className="absolute right-4 top-4 flex flex-col items-end gap-2">
                        <div className="inline-flex items-center rounded-full border border-green-700 bg-green-800/90 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-white shadow-sm">
                          {formatStatusLabel(corper.verification_status)}
                        </div>
                        {corper.is_online ? (
                          <div className="flex flex-col items-center gap-1">
                            <span className="h-2.5 w-2.5 rounded-full bg-lime shadow-[0_0_10px_rgba(124,217,161,0.75)]" />
                            <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-lime">
                              online
                            </span>
                          </div>
                        ) : null}
                      </div>

                      <div className="absolute inset-x-0 bottom-0 px-4 pb-4 pt-20 text-left">
                        <h2 className="font-display text-[1.8rem] leading-none font-semibold text-white">
                          {corper.full_name}
                        </h2>
                      </div>
                    </div>

                    <div className="grid h-[92px] gap-2 px-4 py-2 text-left">
                      <div className="flex min-w-0 items-center gap-2 rounded-[18px] border border-white/10 bg-white/[0.08] px-2 py-1">
                        <StudyIcon className="h-5 w-5 shrink-0 text-electric" />
                        <span className="min-w-0 truncate text-sm text-white/86">
                          {universityName}
                        </span>
                      </div>
                      <div className="flex min-w-0 items-center gap-2 rounded-[18px] border border-white/10 bg-white/[0.08] px-2 py-1">
                        <SkillIcon className="h-5 w-5 shrink-0 text-coral" />
                        <span className="min-w-0 truncate text-sm text-white/86">
                          {qualification || "Primary skill not specified"}
                        </span>
                      </div>
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
