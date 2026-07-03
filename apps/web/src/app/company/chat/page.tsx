"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ChatThread } from "@/components/dashboard/chat-thread";
import { ConversationCounterpart } from "@/components/dashboard/conversation-counterpart";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { buildCompanyChatPath } from "@/lib/app-paths";

type Conversation = {
  id: string;
  counterpart: {
    name: string;
    qualification?: string;
    degree?: string;
    field_of_study?: string;
    location: string;
    image?: string | null;
  };
  unread_count: number;
};

type ConversationResponse = {
  results: Conversation[];
};

// export default function CompanyChatPage() {
//   const { data } = useApiQuery<ConversationResponse>("/chat/conversations/");

//   return (
//     <DashboardShell role="company" title="Chat inbox">
//       <div className="grid gap-6">
//         {data?.results.map((conversation) => (
//           <Link key={conversation.id} href={`/company/chat/${conversation.id}`}>
//             <Card className="py-2">
//               <ConversationCounterpart
//                 name={conversation.counterpart.name}
//                 image={conversation.counterpart.image}
//                 meta={conversation.counterpart.location || "Location not specified"}
//                 fallbackLabel="Corper"
//               />
//               <p className="mt-1 text-xs uppercase tracking-[0.22em] text-electric">
//                 {conversation.unread_count} unread messages
//               </p>
//             </Card>
//           </Link>
//         ))}
//       </div>
//     </DashboardShell>
//   );
// }
export default function CompanyChatPage() {
  return (
    <Suspense fallback={null}>
      <CompanyChatPageContent />
    </Suspense>
  );
}

function CompanyChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data, refetch } = useApiQuery<ConversationResponse>("/chat/conversations/", true, 2000);
  const selectedConversationId = searchParams.get("conversationId");

  if (selectedConversationId) {
    return (
      <DashboardShell role="company" title="Conversation">
        <div className="mx-auto flex w-full max-w-[50rem] flex-col gap-4">
          <button
            type="button"
            onClick={() => router.replace("/company/chat")}
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
    <DashboardShell role="company" title="Chat inbox">
      <div className="grid gap-6">
        {data?.results.map((conversation) => {
          const degree = conversation.counterpart.degree || "Degree not specified";
          const field_of_study = conversation.counterpart.field_of_study || "Field not specified";
          const location = conversation.counterpart.location || "Location not specified";
          const meta = [degree, field_of_study, location].filter(Boolean).join("  .  ");

          return (
            <Link key={conversation.id} href={buildCompanyChatPath(conversation.id)}>
              <Card className="py-1">
                <ConversationCounterpart

                  name={conversation.counterpart.name}
                  image={conversation.counterpart.image}
                  meta={meta}
                  fallbackLabel="Corper"
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
