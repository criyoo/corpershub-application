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

export default function CorperInterestsPage() {
  const { data, loading, error } = useApiQuery<InterestResponse>("/interests/mine/");

  return (
    <DashboardShell role="corper" title="My Interests" hideCorperBanner>
      <CompanyInterestGrid
        interests={data?.results}
        loading={loading}
        error={error}
        emptyTitle="No company interests yet"
        emptyDescription="Companies you show interest in will appear here."
        cardLabel="Interest sent"
      />
    </DashboardShell>
  );
}
