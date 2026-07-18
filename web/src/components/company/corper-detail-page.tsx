"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCompanyChatPath } from "@/lib/app-paths";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import { defaultAppPathForUser } from "@/lib/session";

type CorperDirectoryDetail = {
  id: string;
  full_name: string;
  age: number | null;
  gender: string;
  posting_location_state: string;
  field_of_study: string;
  degree: string;
  university: string;
  graduation_year: number | null;
  nysc_service_year: string;
  nysc_callup_number: string;
  mobile_number: string;
  email: string;
  profile_photo: string | null;
  skill: string;
  bio: string;
  verification_status: string;
  company_interest_saved: boolean;
  corper_has_paid_access: boolean;
};

function InfoCard({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <Card className={`h-full border-white/8 bg-white/[0.05] ${className}`}>
      <p className="text-xs uppercase tracking-[0.22em] text-lime">{label}</p>
      <p className="mt-4 text-sm leading-7 text-white">{value || "Not specified"}</p>
    </Card>
  );
}

function getInitials(value: string) {
  const parts = value
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "C";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

function getFirstName(value: string) {
  return value
    .split(" ")
    .map((part) => part.trim())
    .find(Boolean) || "Corper";
}

function formatStatusLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatLocation(state: string) {
  return state.trim() || "Location not provided";
}

export function CorperDetailPage({
  corperId,
  onBackToDirectory,
}: {
  corperId: string;
  onBackToDirectory?: () => void;
}) {
  const router = useRouter();
  const { hydrated, session } = useAuth();
  const isCompany = hydrated && session?.user.role === "company";
  const corper = useApiQuery<CorperDirectoryDetail>(`/corpers/directory/${corperId}/`, isCompany);
  const [interestSaved, setInterestSaved] = useState(false);
  const [isSavingInterest, setIsSavingInterest] = useState(false);
  const [isStartingChat, setIsStartingChat] = useState(false);

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    if (!session) {
      router.replace("/register/companies");
      return;
    }

    if (session.user.role !== "company") {
      router.replace(defaultAppPathForUser(session.user));
    }
  }, [hydrated, router, session]);

  useEffect(() => {
    setInterestSaved(corper.data?.company_interest_saved ?? false);
  }, [corper.data?.company_interest_saved]);

  async function saveInterest() {
    setIsSavingInterest(true);
    try {
      const response = await apiFetch<{ message: string }>("/interests/corpers/" + corperId + "/express/", {
        method: "POST",
        body: JSON.stringify({})
      });
      setInterestSaved(true);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to save interest.");
    } finally {
      setIsSavingInterest(false);
    }
  }

  async function startChat() {
    if (!interestSaved) {
      toast.error("Please indicate intereset in corper before initiating chat");
      return;
    }

    setIsStartingChat(true);
    try {
      const response = await apiFetch<{ id: string }>("/chat/conversations/initiate/", {
        method: "POST",
        body: JSON.stringify({ corper_id: corperId }),
      });
      router.push(buildCompanyChatPath(response.id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to open chat.");
    } finally {
      setIsStartingChat(false);
    }
  }

  function handleBackToDirectory() {
    if (onBackToDirectory) {
      onBackToDirectory();
      return;
    }
    router.replace("/company/corpers");
  }

  if (!hydrated || !session || session.user.role !== "company") {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="rounded-full border border-white/10 bg-white/[0.08] px-5 py-3 text-sm text-mist backdrop-blur-xl">
          Loading corper details...
        </div>
      </main>
    );
  }

  if (corper.loading && !corper.data) {
    return (
      <main className="min-h-screen px-4 py-6 md:px-8">
        <div className="mx-auto max-w-[1480px]">
          <button
            type="button"
            onClick={handleBackToDirectory}
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to directory
          </button>
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="min-h-[420px] animate-pulse rounded-[36px] border border-white/10 bg-white/[0.08]" />
            <div className="grid gap-4">
              <div className="h-40 animate-pulse rounded-[32px] border border-white/10 bg-white/[0.08]" />
              <div className="h-40 animate-pulse rounded-[32px] border border-white/10 bg-white/[0.08]" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (corper.error || !corper.data) {
    return (
      <main className="min-h-screen px-4 py-6 md:px-8">
        <div className="mx-auto max-w-[1480px]">
          <button
            type="button"
            onClick={handleBackToDirectory}
            className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to directory
          </button>
          <Card className="mt-6 text-center">
            <h1 className="font-display text-3xl text-white">Corper not available</h1>
            <p className="mt-3 text-sm text-mist">
              {corper.error ?? "This corper profile could not be loaded."}
            </p>
          </Card>
        </div>
      </main>
    );
  }

  const photoUrl = corper.data.profile_photo ? resolveMediaUrl(corper.data.profile_photo) : null;
  const qualification = [corper.data.degree, corper.data.field_of_study].filter(Boolean).join(" · ");
  // const firstName = getFirstName(corper.data.full_name);
  const divsize = "rounded-[28px] border border-white/10 bg-[#07140E]/35 px-5 py-1";
  const textname = "text-[10px] uppercase tracking-[0.16em] text-lime";
  const textvalue = "mt-3 text-[14px] text-white/80";
  const chatDisabledByPlan = !corper.data.corper_has_paid_access;

  return (
    <main className="min-h-screen px-4 py-5 md:px-8 lg:px-10">
      <div className="mx-auto max-w-[1080px]">
        <button
          type="button"
          onClick={handleBackToDirectory}
          className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to directory
        </button>

        <section className="mt-6 grid gap-6 lg:grid-cols-[1.0fr_0.9fr]">
          <div className="overflow-hidden rounded-[36px] border border-white/10 bg-white/[0.08] shadow-glow">
            <div className="relative h-full min-h-[420px]">
              {photoUrl ? (
                <img
                  src={photoUrl}
                  alt={corper.data.full_name}
                  className="absolute inset-0 h-full w-full object-cover object-center"
                />
              ) : (
                <div className="flex h-full min-h-[420px] items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(124,217,161,0.4),transparent_40%),linear-gradient(180deg,#1A523B_0%,#103222_58%,#0A1E15_100%)] text-6xl font-semibold text-white">
                  {getInitials(corper.data.full_name)}
                </div>
              )}
              <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(7,20,14,0.18)_0%,rgba(7,20,14,0.34)_38%,rgba(7,20,14,0.92)_100%)]" />
              <div className="absolute left-6 top-6 rounded-full border border-white/15 bg-[#07140E]/75 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                {formatStatusLabel(corper.data.verification_status)}
              </div>
              <div className="absolute inset-x-6 bottom-6">
                <p className="text-sm uppercase tracking-[0.2em] text-lime">
                  {formatLocation(corper.data.posting_location_state)}
                </p>
                <h1 className="mt-3 font-display text-4xl text-white md:text-5xl">
                  {corper.data.full_name}
                </h1>
                <p className="mt-3 text-base text-white/82">
                  {qualification || "Qualification not specified"}
                </p>
              </div>
            </div>
          </div>

          <Card className="flex flex-col justify-between rounded-[36px]">
            <div className="mt-4 grid gap-3">
              <div className={divsize}>
                <p className={textname}>Qualification</p>
                <p className={textvalue}>{qualification || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>University</p>
                <p className={textvalue}>{corper.data.university || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Gender</p>
                <p className={textvalue}>{corper.data.gender || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Skills</p>
                <p className={textvalue}>{corper.data.skill || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Posting state</p>
                <p className={textvalue}>{formatLocation(corper.data.posting_location_state) || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Graduation year</p>
                <p className={textvalue}>{corper.data.graduation_year ? String(corper.data.graduation_year) : "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>NYSC service year</p>
                <p className={textvalue}>{corper.data.nysc_service_year || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>NYSC Callup Number</p>
                <p className={textvalue}>{corper.data.nysc_callup_number || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Mobile Number</p>
                <p className={textvalue}>{corper.data.mobile_number || "Not specified"}</p>
              </div>
              <div className={divsize}>
                <p className={textname}>Email</p>
                <p className={textvalue}><b>{corper.data.email || "Not specified"}</b></p>
              </div>
              <p className="mt-3 text-xs text-lime">
                Show interest first & chat with fully registered corpers.
                <br />
                Chat unlocks only after the corper is fully verified and registered.
              </p>
            </div>

            <div className="mt-4 grid gap-2 py-1 sm:grid-cols-3">
              <Button
                className="h-9 w-full px-4 py-1 text-xs"
                disabled={isSavingInterest || interestSaved}
                onClick={() => void saveInterest()}
              >
                {interestSaved ? "Interest shown" : isSavingInterest ? "Saving..." : "Interested"}
              </Button>
              <Button
                className="h-9 w-full px-4 py-1 text-xs"
                variant="secondary"
                disabled={isStartingChat || chatDisabledByPlan}
                onClick={() => void startChat()}
              >
                {chatDisabledByPlan ? "Chat unavailable" : isStartingChat ? "Opening chat..." : "Chat"}
              </Button>
              <button
                type="button"
                onClick={handleBackToDirectory}
                className="inline-flex h-9 w-full items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-4 py-1 text-xs font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                Browse corpers
              </button>
            </div>
          </Card>
        </section>

        <section className="mt-4 grid gap-5 lg:grid-cols-2">
          <InfoCard
            label="Bio"
            value={corper.data.bio}
            className="min-h-[220px] lg:col-span-2"
          />
        </section>
      </div>
    </main>
  );
}
