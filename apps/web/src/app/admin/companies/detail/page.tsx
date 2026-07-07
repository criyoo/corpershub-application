"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import {
  formatCompanyApprovalStatus,
  formatCompanyVerificationStatus,
  getCompanyApprovalTone,
  getCompanyVerificationTone,
} from "@/lib/company-verification";
import { resolveMediaUrl } from "@/lib/media";

type CompanyAdminDetail = {
  id: string;
  email: string;
  company_name: string;
  company_registration_number: string;
  company_registration_date: string | null;
  tax_identification_number: string;
  company_image: string | null;
  company_location_state: string;
  preferred_deployment_states: string;
  company_location_city: string;
  company_address: string;
  head_office_address: string;
  company_website: string;
  company_sector: string;
  organization_type: string;
  staff_count_range: string;
  placement_type: string;
  monthly_allowance_offered: string;
  accommodation_provided: string;
  ppa_support: string;
  desired_corper_description: string;
  desired_qualification: string;
  desired_age_range: string;
  desired_field_of_study: string;
  desired_university: string;
  desired_posting_states: string;
  desired_skills: string;
  desired_experience: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  directors_name: string;
  director_phone_number: string;
  verification_status: string;
  approval_status: string;
};

type ReviewDecision = "approved" | "rejected" | null;

function DetailItem({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="grid gap-1">
      <p className="text-xs uppercase tracking-[0.22em] text-mist">{label}</p>
      <p className="text-sm text-white">{value?.trim() ? value : "Not provided"}</p>
    </div>
  );
}

export default function AdminCompanyDetailPage() {
  return (
    <Suspense fallback={null}>
      <AdminCompanyDetailPageContent />
    </Suspense>
  );
}

function AdminCompanyDetailPageContent() {
  const searchParams = useSearchParams();
  const companyId = searchParams.get("companyId") ?? "";
  const company = useApiQuery<CompanyAdminDetail>(`/companies/admin/${companyId}/`, Boolean(companyId));
  const [decision, setDecision] = useState<ReviewDecision>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitDecision() {
    if (!company.data || !decision) {
      toast.error("Select approve or reject before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch(`/companies/admin/${company.data.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: decision }),
      });
      await company.refetch();
      setDecision(null);
      toast.success(decision === "approved" ? "Company approved." : "Company rejected.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update verification.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!companyId) {
    return (
      <DashboardShell role="admin" title="Company review">
        <Card>
          <p className="text-sm text-mist">Select a company from the admin companies page to review details.</p>
        </Card>
      </DashboardShell>
    );
  }

  if (!company.data && company.loading) {
    return (
      <DashboardShell role="admin" title="Company review">
        <Card>
          <p className="text-sm text-mist">Loading company details...</p>
        </Card>
      </DashboardShell>
    );
  }

  if (!company.data) {
    return (
      <DashboardShell role="admin" title="Company review">
        <Card>
          <p className="text-sm text-mist">{company.error ?? "Unable to load company details."}</p>
        </Card>
      </DashboardShell>
    );
  }

  const imageUrl = resolveMediaUrl(company.data.company_image);
  const isPending = company.data.approval_status === "pending";

  return (
    <DashboardShell role="admin" title="Company review">
      <div className="grid gap-4">
        <Card className="grid gap-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="grid gap-3">
              <Badge tone={getCompanyVerificationTone(company.data.verification_status)}>
                {formatCompanyVerificationStatus(company.data.verification_status)}
              </Badge>
              <Badge tone={getCompanyApprovalTone(company.data.approval_status)}>
                {formatCompanyApprovalStatus(company.data.approval_status)}
              </Badge>
              <div>
                <h2 className="font-display text-2xl text-white">{company.data.company_name || "Unnamed company"}</h2>
                <p className="mt-2 text-sm text-mist">{company.data.email}</p>
              </div>
            </div>
            {imageUrl ? (
              <div className="h-28 w-28 overflow-hidden rounded-3xl border border-white/10 bg-white/[0.04]">
                <img src={imageUrl} alt={company.data.company_name} className="h-full w-full object-cover" />
              </div>
            ) : null}
          </div>
        </Card>

        <Card className="grid gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Company identity</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <DetailItem label="Registration number" value={company.data.company_registration_number} />
            <DetailItem label="Registration date" value={company.data.company_registration_date} />
            <DetailItem label="Tax identification number" value={company.data.tax_identification_number} />
            <DetailItem label="Sector" value={company.data.company_sector} />
            <DetailItem label="Organisation type" value={company.data.organization_type} />
            <DetailItem label="Number of staff" value={company.data.staff_count_range} />
            <DetailItem label="Website" value={company.data.company_website} />
            <DetailItem label="Contact name" value={company.data.contact_name} />
            <DetailItem label="Contact email" value={company.data.contact_email} />
            <DetailItem label="Contact number" value={company.data.contact_phone} />
            <DetailItem label="Director name" value={company.data.directors_name} />
            <DetailItem label="Director phone" value={company.data.director_phone_number} />
          </div>
        </Card>

        <Card className="grid gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Location and placement</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <DetailItem label="State(s) of operation" value={company.data.company_location_state} />
            <DetailItem
              label="Preferred state of deployment"
              value={company.data.preferred_deployment_states}
            />
            <DetailItem label="City" value={company.data.company_location_city} />
            <DetailItem label="Company address" value={company.data.company_address} />
            <DetailItem label="Head office address" value={company.data.head_office_address} />
            <DetailItem label="Placement type" value={company.data.placement_type} />
            <DetailItem label="Monthly allowance offered" value={company.data.monthly_allowance_offered} />
            <DetailItem label="Accommodation provided" value={company.data.accommodation_provided} />
            <DetailItem label="PPA support" value={company.data.ppa_support} />
          </div>
        </Card>

        <Card className="grid gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Corper requirements</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <DetailItem label="Desired qualification" value={company.data.desired_qualification} />
            <DetailItem label="Desired age range" value={company.data.desired_age_range} />
            <DetailItem label="Desired field of study" value={company.data.desired_field_of_study} />
            <DetailItem label="Desired university" value={company.data.desired_university} />
            <DetailItem label="Desired posting state" value={company.data.desired_posting_states} />
            <DetailItem label="Desired skills" value={company.data.desired_skills} />
          </div>
          <DetailItem label="Desired experience" value={company.data.desired_experience} />
          <DetailItem label="Company summary" value={company.data.desired_corper_description} />
        </Card>

        <Card className="grid gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Verification decision</p>
            <h2 className="mt-3 font-display text-2xl text-white">Approve or reject this company profile</h2>
            <p className="mt-2 text-sm text-mist">
              Review the submitted details and choose one decision below.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex items-start gap-3 rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm text-white">
              <input
                type="checkbox"
                checked={decision === "approved"}
                disabled={!isPending || isSubmitting}
                onChange={(event) => setDecision(event.target.checked ? "approved" : null)}
                className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent accent-[#1FB766]"
              />
              <span>Approve company verification</span>
            </label>
            <label className="flex items-start gap-3 rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-4 text-sm text-white">
              <input
                type="checkbox"
                checked={decision === "rejected"}
                disabled={!isPending || isSubmitting}
                onChange={(event) => setDecision(event.target.checked ? "rejected" : null)}
                className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent accent-[#F97360]"
              />
              <span>Reject company verification</span>
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" disabled={!isPending || !decision || isSubmitting} onClick={() => void submitDecision()}>
              {isSubmitting ? "Saving..." : "Apply decision"}
            </Button>
            {!isPending ? (
              <p className="text-sm text-mist">
                This company is already {formatCompanyApprovalStatus(company.data.approval_status).toLowerCase()}.
              </p>
            ) : null}
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}
