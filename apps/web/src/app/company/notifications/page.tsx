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

type Notification = {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

type NotificationResponse = {
  results: Notification[];
};

type Interest = {
  id: string;
  corper_has_paid_access: boolean;
  corper: {
    id: string;
    full_name: string;
    degree: string;
    field_of_study: string;
    posting_location_state: string;
    profile_photo: string | null;
  };
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

export default function CompanyCorpersInterestedPage() {
  const router = useRouter();
  const notifications = useApiQuery<NotificationResponse>("/notifications/");
  const interests = useApiQuery<InterestResponse>("/interests/received/");

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

  const interestMap = new Map((interests.data?.results ?? []).map((interest) => [interest.id, interest]));
  const interestNotifications = (notifications.data?.results ?? []).filter(
    (notification) => notification.notification_type === "corper_interest_received"
  );

  return (
    <DashboardShell role="company" title="Corpers Interested">
      {((notifications.loading && !notifications.data) || (interests.loading && !interests.data)) ? (
        <Card>
          <p className="text-sm text-mist">Loading interested corpers...</p>
        </Card>
      ) : notifications.error || interests.error ? (
        <Card>
          <p className="text-sm text-mist">{notifications.error ?? interests.error}</p>
        </Card>
      ) : !interestNotifications.length ? (
        <EmptyState
          title="No corpers interested yet"
          description="Corpers who express interest in your company will appear here."
        />
      ) : (
        <div className="grid gap-4">
          {interestNotifications.map((notification) => {
            const interestId =
              typeof notification.data?.interest_id === "string" ? notification.data.interest_id : "";
            const interest = interestMap.get(interestId);
            const photoUrl = resolveMediaUrl(interest?.corper.profile_photo);
            const corperName = interest?.corper.full_name || "Corper";

            return (
              <Card key={notification.id}>
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-start gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/12 bg-white/[0.08] text-lg font-semibold text-white">
                      {photoUrl ? (
                        <img src={photoUrl} alt={corperName} className="h-full w-full object-cover object-[center_18%]" />
                      ) : (
                        getInitials(corperName)
                      )}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <h2 className="font-display text-xl text-white">{corperName}</h2>
                        <span className="rounded-full border border-white/12 bg-white/[0.08] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                          {notification.read_at ? "Seen" : "New"}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-mist">
                        {interest?.corper.degree || "Qualification not specified"} .{" "}
                        {interest?.corper.field_of_study || "Field of study not specified"} .{" "}
                        {interest?.corper.posting_location_state || "Posting state not specified"}
                      </p>
                      <p className="mt-3 text-sm text-white">{notification.body}</p>
                      <p className="mt-3 text-xs uppercase tracking-[0.22em] text-electric">
                        {new Date(notification.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="grid gap-3 md:min-w-[220px]">
                    {interest ? (
                      <>
                        <Link href={buildCompanyCorperDetailPath(interest.corper.id)}>
                          <Button className="w-full" variant="secondary">
                            View profile
                          </Button>
                        </Link>
                        <Button
                          className="w-full"
                          disabled={!interest.corper_has_paid_access}
                          onClick={() => void startChat(interest.id)}
                          variant={interest.corper_has_paid_access ? "primary" : "secondary"}
                        >
                          {interest.corper_has_paid_access ? "Chat with corper" : "Chat unavailable"}
                        </Button>
                      </>
                    ) : null}
                    {!notification.read_at ? (
                      <Button
                        className="w-full"
                        variant="secondary"
                        onClick={async () => {
                          const response = await apiFetch<{ message?: string }>(`/notifications/${notification.id}/read/`, {
                            method: "POST",
                            body: JSON.stringify({})
                          });
                          toast.success(response.message ?? "Marked as seen.");
                          await notifications.refetch();
                        }}
                      >
                        Mark seen
                      </Button>
                    ) : null}
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
