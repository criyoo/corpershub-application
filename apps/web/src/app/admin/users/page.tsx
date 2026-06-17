"use client";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { useApiQuery } from "@/hooks/use-api-query";

type User = {
  id: string;
  email: string;
  role: string;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
};

export default function AdminUsersPage() {
  const users = useApiQuery<{ results: User[] }>("/adminpanel/users/");

  return (
    <DashboardShell role="admin" title="Users">
      <DataTable
        columns={["Email", "Role", "Verified", "Active", "Created"]}
        rows={
          users.data?.results.map((user) => [
            user.email,
            user.role,
            user.email_verified ? "Yes" : "No",
            user.is_active ? "Yes" : "No",
            new Date(user.created_at).toLocaleDateString()
          ]) ?? []
        }
        loading={users.loading}
        emptyTitle="No users"
        emptyDescription="Registered accounts will appear here."
      />
    </DashboardShell>
  );
}
