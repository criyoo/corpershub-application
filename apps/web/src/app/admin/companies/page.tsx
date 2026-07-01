"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { DataTable } from "@/components/dashboard/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import {
  formatCompanyApprovalStatus,
  formatCompanyVerificationStatus,
  getCompanyApprovalTone,
  getCompanyVerificationTone,
} from "@/lib/company-verification";

type Company = {
  id: string;
  company_name: string;
  company_sector: string;
  company_function: string;
  email: string;
  verification_status: string;
  approval_status: string;
};

export default function AdminCompaniesPage() {
  const companies = useApiQuery<{ results: Company[] }>("/companies/admin/");
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(null);

  const sortedCompanies = [...(companies.data?.results ?? [])].sort((left, right) => {
    if (left.approval_status === right.approval_status) {
      return left.company_name.localeCompare(right.company_name);
    }
    if (left.approval_status === "pending") {
      return -1;
    }
    if (right.approval_status === "pending") {
      return 1;
    }
    return left.company_name.localeCompare(right.company_name);
  });

  async function approveCompany(companyId: string) {
    setActiveCompanyId(companyId);
    try {
      await apiFetch(`/companies/admin/${companyId}/`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: "approved" }),
      });
      toast.success("Company approved.");
      await companies.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to verify company.");
    } finally {
      setActiveCompanyId(null);
    }
  }

  async function rejectCompany(companyId: string) {
    setActiveCompanyId(companyId);
    try {
      await apiFetch(`/companies/admin/${companyId}/`, {
        method: "PATCH",
        body: JSON.stringify({ approval_status: "rejected" }),
      });
      toast.success("Company rejected.");
      await companies.refetch();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to reject company.");
    } finally {
      setActiveCompanyId(null);
    }
  }

  return (
    <DashboardShell role="admin" title="Companies">
      <DataTable
        columns={["Company", "Sector", "Function", "Email", "Verification", "Approval", "Action"]}
        rows={
          sortedCompanies.map((company) => [
            company.company_name,
            company.company_sector,
            company.company_function,
            <Link
              key={`${company.id}-email`}
              href={`/admin/companies/detail?companyId=${company.id}`}
              className="text-lime underline-offset-4 transition hover:text-white hover:underline"
            >
              {company.email}
            </Link>,
            <Badge key={`${company.id}-verification`} tone={getCompanyVerificationTone(company.verification_status)}>
              {formatCompanyVerificationStatus(company.verification_status)}
            </Badge>,
            <Badge key={`${company.id}-approval`} tone={getCompanyApprovalTone(company.approval_status)}>
              {formatCompanyApprovalStatus(company.approval_status)}
            </Badge>,
            company.approval_status === "pending" ? (
              <div key={`${company.id}-action`} className="flex flex-wrap gap-2">
                <Link
                  href={`/admin/companies/detail?companyId=${company.id}`}
                  className="inline-flex items-center justify-center rounded-full border border-lime/30 bg-lime/10 px-4 py-2 text-xs font-semibold text-lime transition duration-200 hover:border-lime/60 hover:bg-lime/15"
                >
                  Review details
                </Link>
                <Button
                  type="button"
                  className="px-4 py-2 text-xs"
                  disabled={activeCompanyId === company.id}
                  onClick={() => void approveCompany(company.id)}
                >
                  Verify
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  className="px-4 py-2 text-xs"
                  disabled={activeCompanyId === company.id}
                  onClick={() => void rejectCompany(company.id)}
                >
                  Reject
                </Button>
              </div>
            ) : (
              <span key={`${company.id}-action`} className="text-xs uppercase tracking-[0.18em] text-mist">
                {company.approval_status === "approved"
                  ? "Approved"
                  : company.approval_status === "rejected"
                    ? "Rejected"
                    : "Awaiting submission"}
              </span>
            ),
          ]) ?? []
        }
        loading={companies.loading}
        emptyTitle="No companies"
        emptyDescription="Company profiles will appear here."
      />
    </DashboardShell>
  );
}
