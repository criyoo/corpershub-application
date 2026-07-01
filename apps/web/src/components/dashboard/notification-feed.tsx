"use client";

import Link from "next/link";
import { toast } from "sonner";

import { useApiQuery } from "@/hooks/use-api-query";
import { buildCorperChatPath } from "@/lib/app-paths";
import { apiFetch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

type Notification = {
  id: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

type PaginatedNotifications = {
  results: Notification[];
};

type Conversation = {
  id: string;
  counterpart: {
    id: string;
    role: string;
    name: string;
    location: string;
    sector?: string;
  };
  unread_count: number;
};

type ConversationResponse = {
  results: Conversation[];
};

function getCompanyMonogram(name: string) {
  const parts = name
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "B";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

export function NotificationFeed({ variant = "default" }: { variant?: "default" | "corper-company-cards" }) {
  const { data, loading, refetch } = useApiQuery<PaginatedNotifications>("/notifications/");
  const conversations = useApiQuery<ConversationResponse>("/chat/conversations/", variant === "corper-company-cards");

  if (variant === "corper-company-cards") {
    const companyCards: Array<{ conversation: Conversation; notification: Notification }> = [];
    const conversationMap = new Map((conversations.data?.results ?? []).map((conversation) => [conversation.id, conversation]));

    for (const notification of data?.results ?? []) {
      const conversationId = typeof notification.data?.conversation_id === "string" ? notification.data.conversation_id : null;
      if (!conversationId) {
        continue;
      }

      const conversation = conversationMap.get(conversationId);
      if (!conversation || conversation.counterpart.role !== "company") {
        continue;
      }

      const existing = companyCards.find((item) => item.conversation.counterpart.id === conversation.counterpart.id);
      if (existing) {
        continue;
      }

      companyCards.push({
        conversation,
        notification
      });
    }

    if (loading || conversations.loading) {
      return (
        <div className="grid justify-items-center gap-6 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-[440px] w-full max-w-[320px] rounded-[28px]" />
          <Skeleton className="h-[440px] w-full max-w-[320px] rounded-[28px]" />
          <Skeleton className="h-[440px] w-full max-w-[320px] rounded-[28px]" />
        </div>
      );
    }

    if (!companyCards.length) {
      return (
        <EmptyState
          title="No companies interested yet"
          description="Companies that contact you or respond through chat will appear here as cards."
        />
      );
    }

    return (
      <div className="grid justify-items-center gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {companyCards.map(({ conversation, notification }) => (
          <Card key={notification.id} className="w-full max-w-[320px] overflow-hidden p-0">
            <div className="relative aspect-[4/5] w-full overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(190,227,202,0.32),rgba(17,38,28,0.96))]">
              <div className="flex h-full w-full items-center justify-center text-5xl font-semibold text-white">
                {getCompanyMonogram(conversation.counterpart.name)}
              </div>
              <div className="absolute left-4 top-4 rounded-full border border-white/12 bg-[#07140E]/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                {conversation.counterpart.sector ?? "Company"}
              </div>
              <div className="absolute right-4 top-4 rounded-full border border-white/12 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                {notification.read_at ? "Seen" : "New"}
              </div>
              <div className="absolute inset-x-4 bottom-4 rounded-[20px] border border-white/12 bg-[#07140E]/80 px-4 py-3 text-white">
                <p className="text-xs uppercase tracking-[0.18em] text-lime">Latest update</p>
                <p className="mt-2 text-sm font-semibold">{notification.title}</p>
              </div>
            </div>
            <div className="px-5 py-5">
              <h3 className="font-display text-2xl text-white">{conversation.counterpart.name}</h3>
              <p className="mt-2 text-sm text-mist">{conversation.counterpart.location}</p>
              <p className="mt-4 text-sm leading-6 text-white">{notification.body}</p>
              <div className="mt-5 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.22em] text-electric">
                <span>{new Date(notification.created_at).toLocaleDateString()}</span>
                <span>{conversation.unread_count} unread</span>
              </div>
              <div className="mt-6 grid gap-3">
                <Link
                  href={buildCorperChatPath(conversation.id)}
                  className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#1FB766_0%,#118A48_100%)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_18px_35px_rgba(17,138,72,0.28)] transition duration-200 hover:brightness-105"
                >
                  Open chat
                </Link>
                {!notification.read_at ? (
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      const response = await apiFetch<{ message?: string }>(`/notifications/${notification.id}/read/`, {
                        method: "POST",
                        body: JSON.stringify({})
                      });
                      toast.success(response.message ?? "Marked as seen.");
                      await refetch();
                    }}
                  >
                    Mark seen
                  </Button>
                ) : null}
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="grid gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!data?.results.length) {
    return <EmptyState title="No activity yet" description="New system events will show up here." />;
  }

  return (
    <div className="grid gap-4">
      {data.results.map((notification) => (
        <Card key={notification.id}>
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="font-display text-lg text-white">{notification.title}</h3>
              <p className="mt-2 text-sm text-mist">{notification.body}</p>
              <p className="mt-3 text-xs uppercase tracking-[0.22em] text-electric">
                {new Date(notification.created_at).toLocaleString()}
              </p>
            </div>
            {!notification.read_at ? (
              <Button
                variant="secondary"
                onClick={async () => {
                  const response = await apiFetch<{ message?: string }>(`/notifications/${notification.id}/read/`, {
                    method: "POST",
                    body: JSON.stringify({})
                  });
                  toast.success(response.message ?? "Marked as seen.");
                  await refetch();
                }}
              >
                Mark seen
              </Button>
            ) : null}
          </div>
        </Card>
      ))}
    </div>
  );
}
