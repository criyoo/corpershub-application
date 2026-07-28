"use client";

import { Building2 } from "lucide-react";

import { useApiQuery } from "@/hooks/use-api-query";

type CompaniesResponse = {
  count: number;
  directory_stats?: {
    total_count: number;
  };
};

export function SectorsCompanyStat() {
  const companies = useApiQuery<CompaniesResponse>("/search/companies/?search=", true, 60000, false);
  const totalCompanies = companies.data?.directory_stats?.total_count ?? companies.data?.count ?? 0;

  return (
    <div className="w-full rounded-[24px] border border-white/10 bg-white/[0.07] p-5 shadow-glow sm:max-w-xs lg:justify-self-end">
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-lime/15 text-lime">
          <Building2 className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.18em] text-mist">Registered Companies</p>
          <p className="mt-1 text-3xl font-semibold text-white">{totalCompanies.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}
