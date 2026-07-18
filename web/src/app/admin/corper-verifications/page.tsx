"use client";

import { useState } from "react";
import { toast } from "sonner";

import { DataTable } from "@/components/dashboard/data-table";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import { formatVerificationStatus } from "@/lib/verification";

type CorperVerification = {
  id: string;
  email: string;
  full_name: string;
  profile_created: boolean;
  biodata_verification_status: string;
  masked_nin_number: string;
  masked_callup_number: string;
  nysc_callup_document: string | null;
  masked_state_code: string;
  nysc_state_code_document: string | null;
  verification_status: string;
  nin_verification_status: string;
  nysc_callup_verification_status: string;
  nysc_state_code_verification_status: string;
};

function getStatusTone(status: string): "neutral" | "success" | "warning" {
  if (status === "verified") {
    return "success";
  }

  if (status === "rejected" || status === "failed") {
    return "warning";
  }

  return "neutral";
}

type VerificationField =
  | "biodata_verification_status"
  | "nin_verification_status"
  | "nysc_callup_verification_status"
  | "nysc_state_code_verification_status";

export default function AdminCorperVerificationsPage() {
  const { hydrated, session } = useAuth();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "admin";
  const corpers = useApiQuery<{ results: CorperVerification[] }>("/corpers/admin/verifications/", protectedQueryEnabled);
  const [activeActionId, setActiveActionId] = useState<string | null>(null);

  async function updateStatus(
    corperId: string,
    field: VerificationField,
    value: string
  ) {
    const actionId = `${corperId}-${field}-${value}`;
    setActiveActionId(actionId);
    try {
      await apiFetch(`/corpers/admin/verifications/${corperId}/`, {
        method: "PATCH",
        body: JSON.stringify({ [field]: value }),
      });
      toast.success("Verification status updated.");
      await corpers.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update verification status.");
    } finally {
      setActiveActionId(null);
    }
  }

  return (
    <DashboardShell role="admin" title="Corper verifications">
      <DataTable
        columns={["Corper", "Email", "Profile record", "Overall", "Biodata", "NIN", "NYSC Call-up", "NYSC State Code", "Actions"]}
        rows={
          corpers.data?.results.map((corper) => [
            corper.full_name || "Unnamed corper",
            corper.email,
            corper.profile_created ? (
              <Badge key={`${corper.id}-profile-created`} tone="success">
                Created
              </Badge>
            ) : (
              <Badge key={`${corper.id}-profile-created`} tone="neutral">
                Not started
              </Badge>
            ),
            <Badge key={`${corper.id}-profile-status`} tone={getStatusTone(corper.verification_status)}>
              {formatVerificationStatus(corper.verification_status)}
            </Badge>,
            <Badge key={`${corper.id}-biodata`} tone={getStatusTone(corper.biodata_verification_status)}>
              {formatVerificationStatus(corper.biodata_verification_status)}
            </Badge>,
            <div key={`${corper.id}-nin`} className="grid gap-2">
              <Badge tone={getStatusTone(corper.nin_verification_status)}>
                {formatVerificationStatus(corper.nin_verification_status)}
              </Badge>
              <span className="text-xs uppercase tracking-[0.16em] text-mist">
                {corper.masked_nin_number || "No NIN"}
              </span>
            </div>,
            <div key={`${corper.id}-callup`} className="grid gap-2">
              <Badge tone={getStatusTone(corper.nysc_callup_verification_status)}>
                {formatVerificationStatus(corper.nysc_callup_verification_status)}
              </Badge>
              <span className="text-xs uppercase tracking-[0.16em] text-mist">
                {corper.masked_callup_number || "No call-up"}
              </span>
              {corper.nysc_callup_document ? (
                <a
                  href={resolveMediaUrl(corper.nysc_callup_document) ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-semibold text-lime transition hover:text-white"
                >
                  View document
                </a>
              ) : null}
            </div>,
            <div key={`${corper.id}-state-code`} className="grid gap-2">
              <Badge tone={getStatusTone(corper.nysc_state_code_verification_status)}>
                {formatVerificationStatus(corper.nysc_state_code_verification_status)}
              </Badge>
              <span className="text-xs uppercase tracking-[0.16em] text-mist">
                {corper.masked_state_code || "No state code"}
              </span>
              {corper.nysc_state_code_document ? (
                <a
                  href={resolveMediaUrl(corper.nysc_state_code_document) ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-semibold text-lime transition hover:text-white"
                >
                  View document
                </a>
              ) : null}
            </div>,
            <div key={`${corper.id}-actions`} className="grid gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.18em] text-mist">Biodata</span>
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-biodata_verification_status-verified`}
                  onClick={() => void updateStatus(corper.id, "biodata_verification_status", "verified")}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-biodata_verification_status-rejected`}
                  onClick={() => void updateStatus(corper.id, "biodata_verification_status", "rejected")}
                >
                  Reject
                </Button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.18em] text-mist">NYSC</span>
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-nysc_callup_verification_status-verified`}
                  onClick={() => void updateStatus(corper.id, "nysc_callup_verification_status", "verified")}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-nysc_callup_verification_status-rejected`}
                  onClick={() => void updateStatus(corper.id, "nysc_callup_verification_status", "rejected")}
                >
                  Reject
                </Button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.18em] text-mist">State code</span>
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-nysc_state_code_verification_status-verified`}
                  onClick={() => void updateStatus(corper.id, "nysc_state_code_verification_status", "verified")}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="px-4 py-2 text-xs"
                  disabled={activeActionId === `${corper.id}-nysc_state_code_verification_status-rejected`}
                  onClick={() => void updateStatus(corper.id, "nysc_state_code_verification_status", "rejected")}
                >
                  Reject
                </Button>
              </div>
            </div>,
          ]) ?? []
        }
        loading={corpers.loading}
        emptyTitle="No corper verifications"
        emptyDescription="Corper verification records will appear here for biodata, NIN, call-up, and state code review."
      />
    </DashboardShell>
  );
}
