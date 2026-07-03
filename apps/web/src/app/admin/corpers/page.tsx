"use client";

import { useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";

type Corper = {
  id: string;
  full_name: string;
  email: string;
  university: string;
  degree: string;
  posting_location_state: string;
  is_complete: boolean;
  approval_status: string;
};

export default function AdminCorpersPage() {
  const corpers = useApiQuery<{ results: Corper[] }>("/corpers/admin/");
  const [activeCorperId, setActiveCorperId] = useState<string | null>(null);

  async function updateApprovalStatus(corperId: string, approvalStatus: "approved" | "rejected") {
    setActiveCorperId(corperId);
    try {
      await apiFetch(`/corpers/admin/${corperId}/`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: approvalStatus }),
      });
      toast.success(approvalStatus === "approved" ? "Corper approved." : "Corper rejected.");
      await corpers.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update approval status.");
    } finally {
      setActiveCorperId(null);
    }
  }

  function getApprovalTone(status: string): "neutral" | "warning" | "success" {
    if (status === "approved") {
      return "success";
    }
    if (status === "pending" || status === "rejected") {
      return "warning";
    }
    return "neutral";
  }

  function formatApprovalStatus(status: string) {
    switch (status) {
      case "approved":
        return "Approved";
      case "pending":
        return "Pending";
      case "rejected":
        return "Rejected";
      default:
        return "Unsubmitted";
    }
  }

  return (
    <DashboardShell role="admin" title="Corper profiles">
      <DataTable
        columns={["Name", "Email", "University", "Degree", "Posting state", "Approval", "Action"]}
        rows={
          corpers.data?.results.map((corper) => [
            corper.full_name || "Unnamed corper",
            corper.email,
            corper.university || "Not provided",
            corper.degree || "Not provided",
            corper.posting_location_state || "Not provided",
            <Badge key={`${corper.id}-approval`} tone={getApprovalTone(corper.approval_status)}>
              {formatApprovalStatus(corper.approval_status)}
            </Badge>,
            corper.approval_status === "pending" ? (
              <div key={`${corper.id}-actions`} className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeCorperId === corper.id || !corper.is_complete}
                  onClick={() => void updateApprovalStatus(corper.id, "approved")}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="px-4 py-2 text-xs"
                  disabled={activeCorperId === corper.id}
                  onClick={() => void updateApprovalStatus(corper.id, "rejected")}
                >
                  Reject
                </Button>
              </div>
            ) : (
              <span key={`${corper.id}-actions`} className="text-xs uppercase tracking-[0.18em] text-mist">
                {formatApprovalStatus(corper.approval_status)}
              </span>
            ),
          ]) ?? []
        }
        loading={corpers.loading}
        emptyTitle="No corper profiles"
        emptyDescription="Completed corper profile records will appear here."
      />
    </DashboardShell>
  );
}
