"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import { formatVerificationStatus, formatVerificationType } from "@/lib/verification";

type AttemptDetail = {
  id: string;
  user_email: string;
  corper_name: string;
  verification_type: string;
  status: string;
  submitted_value_masked: string;
  metadata?: Record<string, unknown>;
  reviewer_email: string | null;
  review_note: string;
  document_name: string | null;
  document_url: string | null;
  created_at: string;
  updated_at: string;
};

function getStatusTone(status: string): "neutral" | "success" | "warning" {
  if (status === "approved") {
    return "success";
  }
  if (status === "rejected" || status === "failed") {
    return "warning";
  }
  return "neutral";
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2 rounded-[24px] border border-white/10 bg-white/[0.04] px-5 py-4">
      <p className="text-xs uppercase tracking-[0.22em] text-lime">{label}</p>
      <p className="text-sm text-white">{value || "Not provided"}</p>
    </div>
  );
}

export function AdminVerificationAttemptDetailPage({ attemptId }: { attemptId: string }) {
  const { hydrated, session } = useAuth();
  const protectedQueryEnabled =
    hydrated && Boolean(session) && session?.user.role === "admin" && Boolean(attemptId);
  const attempt = useApiQuery<AttemptDetail>(
    `/verification/attempts/${attemptId}/`,
    protectedQueryEnabled
  );
  const [isReviewing, setIsReviewing] = useState(false);
  const biodataMetadata =
    attempt.data?.verification_type === "biodata" ? (attempt.data.metadata ?? {}) : null;

  async function reviewAttempt(status: "approved" | "rejected") {
    setIsReviewing(true);
    try {
      await apiFetch(`/verification/attempts/${attemptId}/review/`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      toast.success(`Verification ${status}.`);
      await attempt.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to review verification.");
    } finally {
      setIsReviewing(false);
    }
  }

  return (
    <DashboardShell role="admin" title="Verification attempt">
      <div className="grid gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/admin/verifications/"
            className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
          >
            Back to attempts
          </Link>
        </div>

        {!attempt.data && attempt.loading ? (
          <Card>
            <p className="text-sm text-mist">Loading verification attempt...</p>
          </Card>
        ) : attempt.error || !attempt.data ? (
          <Card>
            <p className="text-sm text-mist">
              {attempt.error ?? "Unable to load this verification attempt right now."}
            </p>
          </Card>
        ) : (
          <>
            <Card className="grid gap-4">
              <div className="flex flex-col gap-4 border-b border-white/10 pb-5 lg:flex-row lg:items-center lg:justify-between">
                <div className="grid gap-2">
                  <p className="text-xs uppercase tracking-[0.22em] text-lime">User</p>
                  <h2 className="font-display text-3xl text-white">{attempt.data.user_email}</h2>
                  <p className="text-sm text-mist">
                    {formatVerificationType(attempt.data.verification_type)} verification attempt
                  </p>
                </div>
                <Badge tone={getStatusTone(attempt.data.status)}>
                  {formatVerificationStatus(attempt.data.status)}
                </Badge>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <DetailField label="Masked value" value={attempt.data.submitted_value_masked} />
                <DetailField label="Corper name" value={attempt.data.corper_name} />
                <DetailField
                  label="Created"
                  value={new Date(attempt.data.created_at).toLocaleString()}
                />
                <DetailField
                  label="Last updated"
                  value={new Date(attempt.data.updated_at).toLocaleString()}
                />
                <DetailField label="Reviewed by" value={attempt.data.reviewer_email ?? ""} />
                <DetailField label="Review note" value={attempt.data.review_note} />
              </div>

              {biodataMetadata ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <DetailField
                    label="Submitted full name"
                    value={String(biodataMetadata.full_name ?? "")}
                  />
                  <DetailField
                    label="Submitted date of birth"
                    value={String(biodataMetadata.date_of_birth ?? "")}
                  />
                  <DetailField
                    label="Submitted matric number"
                    value={String(biodataMetadata.university_matriculation_number ?? "")}
                  />
                </div>
              ) : null}

              {attempt.data.document_url ? (
                <div className="rounded-[24px] border border-white/10 bg-white/[0.04] px-5 py-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-lime">Submitted document</p>
                  <a
                    href={resolveMediaUrl(attempt.data.document_url) ?? "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex text-sm font-semibold text-white transition hover:text-lime"
                  >
                    {attempt.data.document_name || "View uploaded document"}
                  </a>
                </div>
              ) : null}
            </Card>

            <Card className="grid gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Review</p>
                <h3 className="mt-2 font-display text-2xl text-white">Approve or reject this attempt</h3>
              </div>
              {attempt.data.status === "pending" ? (
                <div className="flex flex-wrap gap-3">
                  <Button
                    type="button"
                    disabled={isReviewing}
                    onClick={() => void reviewAttempt("approved")}
                  >
                    Approve
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    disabled={isReviewing}
                    onClick={() => void reviewAttempt("rejected")}
                  >
                    Reject
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-mist">
                  This attempt has already been {formatVerificationStatus(attempt.data.status).toLowerCase()}.
                </p>
              )}
            </Card>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
