"use client";

import { CompanyInterestGrid } from "@/components/corper/company-interest-grid";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useApiQuery } from "@/hooks/use-api-query";
import type { CompanyDirectorySummary } from "@/lib/company-directory";

type Interest = {
  id: string;
  status: string;
  message: string;
  corper_expressed_at: string | null;
  company_expressed_at: string | null;
  company: CompanyDirectorySummary;
};

type InterestResponse = {
  results: Interest[];
};

export default function CorperCompaniesInterestedPage() {
  const { data, loading, error } = useApiQuery<InterestResponse>("/interests/companies/received/");

  return (
    <DashboardShell role="corper" title="Companies Interested" hideCorperBanner>
      <CompanyInterestGrid
        interests={data?.results}
        loading={loading}
        error={error}
        emptyTitle="No companies interested yet"
        emptyDescription="Companies that show interest in you will appear here."
        cardLabel="Interested"
      />
    </DashboardShell>
  );
}
