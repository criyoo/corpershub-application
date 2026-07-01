"use client";

import { useState } from "react";
import { toast } from "sonner";

import { DataTable } from "@/components/dashboard/data-table";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";

type AdminAccessRequest = {
  id: string;
  email: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  notification_sent_at: string | null;
  created_at: string;
};

function getStatusTone(status: AdminAccessRequest["status"]) {
  if (status === "approved") {
    return "success";
  }
  if (status === "rejected") {
    return "warning";
  }
  return "neutral";
}

function formatStatus(status: AdminAccessRequest["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function AdminAccessRequestsPage() {
  const requests = useApiQuery<{ results: AdminAccessRequest[] }>("/adminpanel/admin-registration-requests/");
  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);

  const sortedRequests = [...(requests.data?.results ?? [])].sort((left, right) => {
    if (left.status === right.status) {
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    }
    if (left.status === "pending") {
      return -1;
    }
    if (right.status === "pending") {
      return 1;
    }
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });

  async function updateRequestStatus(requestId: string, status: "approved" | "rejected") {
    setActiveRequestId(requestId);
    try {
      await apiFetch(`/adminpanel/admin-registration-requests/${requestId}/`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      toast.success(status === "approved" ? "Admin access approved." : "Admin access rejected.");
      await requests.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update admin access request.");
    } finally {
      setActiveRequestId(null);
    }
  }

  return (
    <DashboardShell role="admin" title="Admin Access Requests">
      <div className="grid gap-4">
        <p className="max-w-3xl text-sm leading-7 text-mist">
          The first admin account is created immediately by the backend. Every later admin registration request stays here until an existing admin approves or rejects it.
        </p>

        <DataTable
          columns={["Email", "Requested", "Status", "Primary admin notified", "Reviewed by", "Action"]}
          rows={
            sortedRequests.map((request) => [
              request.email,
              new Date(request.created_at).toLocaleString(),
              <Badge key={`${request.id}-status`} tone={getStatusTone(request.status)}>
                {formatStatus(request.status)}
              </Badge>,
              request.notification_sent_at ? new Date(request.notification_sent_at).toLocaleString() : "Not yet",
              request.reviewed_by_email
                ? `${request.reviewed_by_email} · ${request.reviewed_at ? new Date(request.reviewed_at).toLocaleString() : ""}`
                : "Awaiting review",
              request.status === "pending" ? (
                <div key={`${request.id}-actions`} className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    className="px-4 py-2 text-xs"
                    disabled={activeRequestId === request.id}
                    onClick={() => void updateRequestStatus(request.id, "approved")}
                  >
                    Approve
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    className="px-4 py-2 text-xs"
                    disabled={activeRequestId === request.id}
                    onClick={() => void updateRequestStatus(request.id, "rejected")}
                  >
                    Reject
                  </Button>
                </div>
              ) : (
                <span key={`${request.id}-actions`} className="text-xs uppercase tracking-[0.18em] text-mist">
                  {formatStatus(request.status)}
                </span>
              ),
            ]) ?? []
          }
          loading={requests.loading}
          emptyTitle="No admin access requests"
          emptyDescription="Submitted admin access requests will appear here for review."
        />
      </div>
    </DashboardShell>
  );
}
