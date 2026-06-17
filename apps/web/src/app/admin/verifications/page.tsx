"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { DataTable } from "@/components/dashboard/data-table";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { formatVerificationStatus, formatVerificationType } from "@/lib/verification";

type Attempt = {
  id: string;
  user_email: string;
  verification_type: string;
  status: string;
  submitted_value_masked: string;
  created_at: string;
};

export default function AdminVerificationsPage() {
  const { hydrated, session } = useAuth();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "admin";
  const attempts = useApiQuery<{ results: Attempt[] }>("/verification/attempts/", protectedQueryEnabled);
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null);

  async function reviewAttempt(attemptId: string, status: "approved" | "rejected") {
    setActiveReviewId(attemptId);
    try {
      await apiFetch(`/verification/attempts/${attemptId}/review/`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      toast.success(`Verification ${status}.`);
      await attempts.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to review verification.");
    } finally {
      setActiveReviewId(null);
    }
  }

  return (
    <DashboardShell role="admin" title="Verification attempts">
      <DataTable
        columns={["User", "Type", "Status", "Masked value", "Created", "Action"]}
        rows={
          attempts.data?.results.map((attempt) => [
            <Link
              key={`${attempt.id}-user`}
              href={`/admin/verifications/detail?attemptId=${attempt.id}`}
              className="font-medium text-white underline decoration-white/20 underline-offset-4 transition hover:text-lime hover:decoration-lime/60"
            >
              {attempt.user_email}
            </Link>,
            formatVerificationType(attempt.verification_type),
            formatVerificationStatus(attempt.status),
            attempt.submitted_value_masked,
            new Date(attempt.created_at).toLocaleString(),
            attempt.status === "pending" ? (
              <div className="flex flex-wrap gap-2" key={attempt.id}>
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeReviewId === attempt.id}
                  onClick={() => void reviewAttempt(attempt.id, "approved")}
                >
                  Approve
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="rounded-full px-4 py-2 text-xs"
                  disabled={activeReviewId === attempt.id}
                  onClick={() => void reviewAttempt(attempt.id, "rejected")}
                >
                  Reject
                </Button>
              </div>
            ) : (
              <span className="text-xs uppercase tracking-[0.18em] text-mist">
                {formatVerificationStatus(attempt.status)}
              </span>
            ),
          ]) ?? []
        }
        loading={attempts.loading}
        emptyTitle="No verification attempts"
        emptyDescription="Verification submissions will appear here."
      />
    </DashboardShell>
  );
}
