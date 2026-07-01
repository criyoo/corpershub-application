"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ChatThread } from "@/components/dashboard/chat-thread";
import { ConversationCounterpart } from "@/components/dashboard/conversation-counterpart";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCorperChatPath } from "@/lib/app-paths";
import { getBillingPathForRole, isPaidAccessRequiredMessage } from "@/lib/subscriptions";

type Conversation = {
  id: string;
  counterpart: { name: string; location: string; sector?: string; image?: string | null };
  unread_count: number;
};

type ConversationResponse = {
  results: Conversation[];
};

export default function CorperChatPage() {
  return (
    <Suspense fallback={null}>
      <CorperChatPageContent />
    </Suspense>
  );
}

function CorperChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data, error, refetch } = useApiQuery<ConversationResponse>("/chat/conversations/", true, 2000);
  const selectedConversationId = searchParams.get("conversationId");

  if (selectedConversationId) {
    return (
      <DashboardShell role="corper" title="Conversation" hideCorperBanner>
        <div className="mx-auto flex w-full max-w-[50rem] flex-col gap-4">
          <button
            type="button"
            onClick={() => router.replace("/corper/chat")}
            className="inline-flex w-fit items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
          >
            Back to inbox
          </button>
          <ChatThread conversationId={selectedConversationId} onConversationStateChange={refetch} />
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell role="corper" title="Chat inbox" hideCorperBanner>
      {error ? (
        <Card className="border-coral/30 bg-coral/10">
          <h2 className="font-display text-2xl text-white">Unable to load conversations</h2>
          <p className="mt-3 text-sm text-mist">{error}</p>
          {isPaidAccessRequiredMessage(error) ? (
            <Link
              href={getBillingPathForRole("corper")}
              className="mt-5 inline-flex items-center justify-center rounded-full border border-lime/30 bg-lime/10 px-5 py-2.5 text-sm font-semibold text-[#E6D28C] transition duration-200 hover:border-lime/60 hover:bg-lime/15 hover:text-[#E6D28C]"
            >
              Upgrade now
            </Link>
          ) : null}
        </Card>
      ) : null}

      <div className="grid gap-2">
        {data?.results.map((conversation) => {
          const sector = conversation.counterpart.sector || "Sector not specified";
          const location = conversation.counterpart.location || "Location not specified";
          const meta = [sector, location].filter(Boolean).join("  .  ");

          return (
            <Link key={conversation.id} href={buildCorperChatPath(conversation.id)}>
              <Card className="py-2">
                <ConversationCounterpart 
                  name={conversation.counterpart.name}
                  image={conversation.counterpart.image}
                  meta={meta}
                  fallbackLabel="Company"
                />
                <p className="mt-0.8 uppercase tracking-[0.14em] text-green-400 text-xs text-electric">
                  <b>{conversation.unread_count} unread messages</b>
                </p>
              </Card>
            </Link>
          );
        })}
      </div>
    </DashboardShell>
  );
}
