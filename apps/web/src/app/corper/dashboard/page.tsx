"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { useApiQuery } from "@/hooks/use-api-query";
import { formatSubscriptionPlanLabel, formatSubscriptionStatus } from "@/lib/subscriptions";

type OverviewStats = {
  verification_credentials_outstanding: number;
  received_interest_count: number;
  sent_interest_count: number;
  unread_message_count: number;
  conversation_count: number;
  online_count: number;
  corpers_online_count: number;
  community_unread_count: number;
  strong_match_count: number;
  current_subscription_plan: string | null;
  current_subscription_status: string | null;
};

export default function CorperDashboardPage() {
  const overview = useApiQuery<OverviewStats>("/common/dashboard-overview/", undefined, 5000);
  const currentSubscriptionPlan = formatSubscriptionPlanLabel(overview.data?.current_subscription_plan);
  const currentSubscriptionStatus = overview.data?.current_subscription_status
    ? formatSubscriptionStatus(overview.data.current_subscription_status)
    : undefined;

  return (
    <DashboardShell role="corper" title="Corper overview" hideCorperBanner>
      <StatsGrid
        columns="two"
        items={[
          {
            label: "Verification credentials outstanding",
            value: overview.data?.verification_credentials_outstanding ?? 0,
            span: "full"
          },
          { label: "Companies interested", value: overview.data?.received_interest_count ?? 0 },
          { label: "Your interest in companies", value: overview.data?.sent_interest_count ?? 0 },
          { label: "Unread company messages", value: overview.data?.unread_message_count ?? 0 },
          { label: "Unread community messages", value: overview.data?.community_unread_count ?? 0 },
          { label: "Companies with match score above 50%", value: overview.data?.strong_match_count ?? 0 },
          { label: "Conversations started", value: overview.data?.conversation_count ?? 0 },
          { label: "Companies online", value: overview.data?.online_count ?? 0 },
          { label: "Corpers cnline", value: overview.data?.corpers_online_count ?? 0 },

          {
            label: "Current subscription plan",
            value: currentSubscriptionPlan,
            caption: currentSubscriptionStatus,
            span: "full"
          }
        ]}
      />
    </DashboardShell>
  );
}
