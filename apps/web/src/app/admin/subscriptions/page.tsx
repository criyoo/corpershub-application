"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { useApiQuery } from "@/hooks/use-api-query";
import { formatBillingInterval } from "@/lib/subscriptions";

type Plan = {
  name: string;
  code: string;
  amount_naira: number;
  billing_interval: string;
  applies_to: string;
  is_active: boolean;
};

export default function AdminSubscriptionsPage() {
  const plans = useApiQuery<{ results: Plan[] }>("/subscriptions/plans/");

  return (
    <DashboardShell role="admin" title="Subscription plans">
      <DataTable
        columns={["Plan", "Code", "Amount", "Interval", "Role", "Active"]}
        rows={
          plans.data?.results.map((plan) => [
            plan.name,
            plan.code,
            `₦${plan.amount_naira.toLocaleString()}`,
            formatBillingInterval(plan.billing_interval),
            plan.applies_to,
            plan.is_active ? "Yes" : "No"
          ]) ?? []
        }
        loading={plans.loading}
        emptyTitle="No plans"
        emptyDescription="Subscription plans will appear here."
      />
    </DashboardShell>
  );
}
