"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useHomeBackgroundImageUrls } from "@/hooks/use-home-background-image-urls";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { buildCorperChatPath } from "@/lib/app-paths";
import {
  formatCompanyDirectoryLabel,
  getCompanyDirectoryImage,
  getCompanyMonogram,
  type CompanyDirectoryDetail,
} from "@/lib/company-directory";
import { defaultAppPathForUser } from "@/lib/session";
import {
  type BillingSubscriptionResponse,
  getBillingPathForRole,
  hasPaidCorperAccess,
  isBrowseRestrictionMessage,
} from "@/lib/subscriptions";

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <Card className="h-full border-white/8 bg-white/[0.05] py-2">
      <p className="text-xs uppercase tracking-[0.22em] text-lime">{label}</p>
      <p className="mt-4 text-sm leading-7 text-white">{value || "Not specified"}</p>
    </Card>
  );
}

function getRecommendationLabel(score: number) {
  if (score >= 75) {
    return "Top match";
  }
  if (score >= 50) {
    return "Strong match";
  }
  if (score > 0) {
    return "Recommended";
  }
  return "";
}

export function CompanyDetailPage({
  companyId,
  imageUrls = [],
}: {
  companyId: string;
  imageUrls?: string[];
}) {
  const router = useRouter();
  const { hydrated, session } = useAuth();
  const backgroundImageUrls = useHomeBackgroundImageUrls(imageUrls);
  const isCorper = hydrated && session?.user.role === "corper";
  const company = useApiQuery<CompanyDirectoryDetail>(`/companies/directory/${companyId}/`, isCorper);
  const subscriptions = useApiQuery<BillingSubscriptionResponse>("/subscriptions/me/", isCorper);
  const [interestShown, setInterestShown] = useState(false);
  const [isSavingInterest, setIsSavingInterest] = useState(false);
  const [isStartingChat, setIsStartingChat] = useState(false);

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    if (!session) {
      router.replace("/register/corpers");
      return;
    }

    if (session.user.role !== "corper") {
      router.replace(defaultAppPathForUser(session.user));
    }
  }, [hydrated, router, session]);

  useEffect(() => {
    setInterestShown(company.data?.corper_has_expressed_interest ?? false);
  }, [company.data?.corper_has_expressed_interest]);

  async function expressInterest() {
    setIsSavingInterest(true);
    try {
      const response = await apiFetch<{ message: string }>(`/interests/companies/${companyId}/express/`, {
        method: "POST",
        body: JSON.stringify({})
      });
      setInterestShown(true);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to express interest.");
    } finally {
      setIsSavingInterest(false);
    }
  }

  async function startChat() {
    if (!interestShown) {
      toast.error("Please indicate intereset in company before initiating chat");
      return;
    }

    if (!company.data?.company_has_expressed_interest) {
      toast.error("Please wait for company to indicate intereset before initiating chat");
      return;
    }

    setIsStartingChat(true);
    try {
      const response = await apiFetch<{ id: string }>("/chat/conversations/initiate/", {
        method: "POST",
        body: JSON.stringify({ company_id: companyId })
      });
      router.push(buildCorperChatPath(response.id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to open chat.");
    } finally {
      setIsStartingChat(false);
    }
  }

  if (!hydrated || !session || session.user.role !== "corper") {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-full border border-white/10 bg-white/[0.08] px-5 py-3 text-sm text-mist backdrop-blur-xl">
          Loading company details...
        </div>
      </main>
    );
  }

  if (company.loading && !company.data) {
    return (
      <main className="min-h-screen px-4 py-6 md:px-8">
        <div className="mx-auto max-w-[1480px]">
          <Link
            href="/corper/companies"
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to directory
          </Link>
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="aspect-[4/3] animate-pulse rounded-[36px] border border-white/10 bg-white/[0.08]" />
            <div className="grid gap-4">
              <div className="h-32 animate-pulse rounded-[32px] border border-white/10 bg-white/[0.08]" />
              <div className="h-48 animate-pulse rounded-[32px] border border-white/10 bg-white/[0.08]" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (company.error || !company.data) {
    return (
      <main className="min-h-screen px-4 py-6 md:px-8">
        <div className="mx-auto max-w-[1480px]">
          <Link
            href="/corper/companies"
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to directory
          </Link>
          <Card className="mt-6 text-center">
            <h1 className="font-display text-3xl text-white">Company not available</h1>
            <p className="mt-3 text-sm text-mist">
              {company.error ?? "This company could not be loaded."}
            </p>
            {isBrowseRestrictionMessage(company.error) ? (
              <Link
                href={getBillingPathForRole("corper")}
                className="mt-5 inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                Open billing
              </Link>
            ) : null}
          </Card>
        </div>
      </main>
    );
  }

  const imageUrl = getCompanyDirectoryImage(
    backgroundImageUrls,
    company.data.id,
    company.data.company_image
  );
  const matchScore = company.data.match_score;
  const hasRecommendation = matchScore !== null;
  const subscriptionsLoaded = !subscriptions.loading || Boolean(subscriptions.data);
  const corperHasPaidAccess = hasPaidCorperAccess(subscriptions.data?.results ?? []);
  const recommendationLabel = hasRecommendation
    ? getRecommendationLabel(matchScore)
    : "";
  const recommendationReason = company.data.match_reasons[0] ?? "";
  const chatDisabledByPlan = !subscriptionsLoaded || !corperHasPaidAccess;
  const companyMeta = [company.data.company_sector]
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" · ");

  return (
    <main className="min-h-screen px-4 py-5 md:px-8 lg:px-10">
      <div className="mx-auto max-w-[1480px]">
        <Link
          href="/corper/companies"
          className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to directory
        </Link>

        <section className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="relative min-h-[420px] overflow-hidden rounded-[36px] border border-white/10 bg-white/[0.08] shadow-glow">
            {imageUrl ? (
              <Image
                alt=""
                aria-hidden="true"
                className="object-cover"
                fill
                sizes="(max-width: 1024px) 100vw, 60vw"
                src={imageUrl}
                unoptimized
              />
            ) : null}
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(7,20,14,0.12)_0%,rgba(7,20,14,0.32)_42%,rgba(7,20,14,0.94)_100%)]" />
            {hasRecommendation && recommendationLabel ? (
              <div className="absolute left-6 top-6 rounded-full border border-lime/40 bg-[#07140E]/80 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-lime backdrop-blur-sm">
                {recommendationLabel} · {matchScore}%
              </div>
            ) : null}

            <div className="absolute inset-x-6 bottom-6">
              <div className="flex items-end gap-4">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-[24px] border border-white/12 bg-white/10 text-xl font-semibold text-white backdrop-blur-md">
                  {getCompanyMonogram(company.data.company_name)}
                </div>
                <div className="min-w-0">
                  <p className="text-sm uppercase tracking-[0.2em] text-lime"><b>{company.data.location}</b></p>
                  <h1 className="mt-2 font-display text-4xl text-white md:text-2xl">
                    {company.data.company_name}
                  </h1>
                  <p className="mt-3 text-base text-white/80">{companyMeta || "Company details pending"}</p>
                </div>
              </div>
            </div>
          </div>

          <Card className="flex flex-col justify-between rounded-[36px]">
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired qualification</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_qualification}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired age range</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_age_range}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired field of study</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_field_of_study}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired university</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_university}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired posting state</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_posting_states}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Desired skills</p>
                <p className="mt-3 text-sm text-white">{company.data.desired_skills}</p>
              </div>
              <div className="rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-4 sm:col-span-2">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Recommendation</p>
                <p className="mt-3 text-sm leading-7 text-white">
                  {hasRecommendation
                    ? recommendationReason || "No recommendation details available yet."
                    : "Recommendation details are not available for this view."}
                </p>
              </div>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {!subscriptionsLoaded ? (
                <Button className="flex-1" disabled variant="secondary">
                  Checking plan...
                </Button>
              ) : corperHasPaidAccess ? (
                <Button
                  className={
                    interestShown
                      ? "flex-1 border-white/10 bg-white/[0.14] text-white/70 shadow-none hover:border-white/10 hover:bg-white/[0.14]"
                      : "flex-1"
                  }
                  disabled={isSavingInterest || interestShown}
                  onClick={() => void expressInterest()}
                  variant={interestShown ? "secondary" : "primary"}
                >
                  {interestShown ? "Interest shown" : isSavingInterest ? "Sending..." : "I\u0027m interested"}
                </Button>
              ) : (
                <Link
                  href={getBillingPathForRole("corper")}
                  className="inline-flex flex-1 items-center justify-center rounded-full border border-lime/30 bg-lime/10 px-5 py-2.5 text-sm font-semibold text-[#E6D28C] transition duration-200 hover:border-lime/60 hover:bg-lime/15 hover:text-[#E6D28C]"
                >
                  Upgrade to show interest
                </Link>
              )}
              <Button
                className="flex-1"
                disabled={chatDisabledByPlan || isStartingChat}
                onClick={() => void startChat()}
                variant="secondary"
              >
                {chatDisabledByPlan ? "Chat locked" : isStartingChat ? "Opening chat..." : "Chat"}
              </Button>
              <Link
                href="/corper/companies"
                className="inline-flex flex-1 items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                Browse more companies
              </Link>
            </div>
          </Card>
        </section>

        <section className="mt-4 grid gap-5 lg:grid-cols-2">
          <DetailItem label="State" value={company.data.company_location_state} />
          <DetailItem label="City" value={company.data.company_location_city} />
          <DetailItem label="Sector" value={company.data.company_sector} />
          <DetailItem label="Desired Field of Study" value={company.data.desired_field_of_study} />
          <DetailItem label="Desired Qualification" value={company.data.desired_qualification} />
          <DetailItem label="Desired Skills" value={company.data.desired_skills} />
          <DetailItem label="Desired Experience" value={company.data.desired_experience} />
        </section>

        <section className="mt-6">
          <Card className="border-white/8 bg-white/[0.05]">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Company Summary</p>
            <p className="mt-5 text-base leading-8 text-white whitespace-pre-wrap">{company.data.summary_description || "Not specified"}</p>
          </Card>
        </section>
      </div>
    </main>
  );
}
