"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { useApiQuery } from "@/hooks/use-api-query";

type Audit = {
  actor_email: string | null;
  action: string;
  target_type: string;
  created_at: string;
};

export default function AdminAuditPage() {
  const audit = useApiQuery<{ results: Audit[] }>("/adminpanel/audit/");

  return (
    <DashboardShell role="admin" title="Audit log">
      <DataTable
        columns={["Actor", "Action", "Target", "Timestamp"]}
        rows={
          audit.data?.results.map((entry) => [
            entry.actor_email ?? "System",
            entry.action,
            entry.target_type,
            new Date(entry.created_at).toLocaleString()
          ]) ?? []
        }
        loading={audit.loading}
        emptyTitle="No audit activity"
        emptyDescription="Sensitive platform actions will appear here."
      />
    </DashboardShell>
  );
}
