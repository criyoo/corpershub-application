"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCompanyChatPath, buildCompanyCorperDetailPath } from "@/lib/app-paths";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";

type Interest = {
  id: string;
  corper_expressed_at: string | null;
  corper_has_paid_access: boolean;
  corper: {
    id: string;
    full_name: string;
    field_of_study: string;
    degree: string;
    university: string;
    skill: string;
    posting_location_state: string;
    profile_photo: string | null;
  };
  message: string;
};

type InterestResponse = {
  results: Interest[];
};

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

export default function CompanyInterestsPage() {
  const router = useRouter();
  const { data, loading, error } = useApiQuery<InterestResponse>("/interests/saved/");

  async function startChat(interestId: string) {
    try {
      const response = await apiFetch<{ id: string }>("/chat/conversations/initiate/", {
        method: "POST",
        body: JSON.stringify({ interest_id: interestId })
      });
      router.push(buildCompanyChatPath(response.id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to start chat.");
    }
  }

  return (
    <DashboardShell role="company" title="Interest">
      {loading && !data ? (
        <Card>
          <p className="text-sm text-mist">Loading your interest list...</p>
        </Card>
      ) : error ? (
        <Card>
          <p className="text-sm text-mist">{error}</p>
        </Card>
      ) : !data?.results.length ? (
        <EmptyState
          title="No corpers in Interest yet"
          description="Use the Interested in corper button on a corper profile to add a photo card here."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.results.map((interest) => {
            const photoUrl = resolveMediaUrl(interest.corper.profile_photo);

            return (
              <Card key={interest.id} className="grid h-[420px] grid-rows-[4fr_2fr] p-2">
                <div className="h-full overflow-hidden rounded-[30px] border border-white/10">
                  <div className="relative h-full w-full bg-[radial-gradient(circle_at_top,_rgba(190,227,202,0.32),rgba(17,38,28,0.96))]">
                    {photoUrl ? (
                      <img
                        src={photoUrl}
                        alt={interest.corper.full_name}
                        className="h-full w-full object-cover object-[center_18%]"
                        
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-5xl font-semibold text-white">
                        {getInitials(interest.corper.full_name)}
                      </div>
                    )}
                  </div>
                </div>
                <div className="grid content-start gap-3 px-2 pb-3 pt-3">
                  <div>
                    <h3 className="font-display text-2xl text-white">{interest.corper.full_name}</h3>
                    <p className="mt-2 text-sm text-mist">
                      {interest.corper.degree || "Qualification not specified"} ·{" "}
                      {interest.corper.field_of_study || "Field not specified"} ·{" "}
                      {interest.corper.posting_location_state || "Location not specified"}
                    </p>
                  </div>

                  {interest.message ? <p className="text-sm text-mist">Message: {interest.message}</p> : null}
                  <div className="grid gap-2">
                    <Link href={buildCompanyCorperDetailPath(interest.corper.id)}>
                      <Button className="h-6 w-full px-2 py-1 text-[12px]" variant="secondary">
                        View profile
                      </Button>
                    </Link>
                    <Button
                      className="h-6 w-full px-2 py-1 text-[12px]"
                      disabled={!interest.corper_has_paid_access}
                      onClick={() => void startChat(interest.id)}
                      variant={interest.corper_has_paid_access ? "primary" : "secondary"}
                    >
                      {interest.corper_has_paid_access ? "Chat with corper" : "Chat unavailable"}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </DashboardShell>
  );
}
