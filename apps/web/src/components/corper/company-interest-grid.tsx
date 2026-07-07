"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { buildCorperCompanyDetailPath } from "@/lib/app-paths";
import { resolveMediaUrl } from "@/lib/media";
import { getCompanyMonogram, type CompanyDirectorySummary } from "@/lib/company-directory";

type CompanyInterest = {
  id: string;
  status: string;
  message: string;
  corper_expressed_at: string | null;
  company_expressed_at: string | null;
  company: CompanyDirectorySummary;
};

const fallbackPhotoBackgrounds = [
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.12),rgba(9,32,19,0.72)),radial-gradient(circle_at_top,rgba(124,217,161,0.55),transparent_45%),linear-gradient(180deg,#4D7C5D_0%,#173727_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.15),rgba(9,32,19,0.78)),radial-gradient(circle_at_top_left,rgba(255,214,102,0.4),transparent_36%),linear-gradient(180deg,#7D6541_0%,#1D2418_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.12),rgba(9,32,19,0.72)),radial-gradient(circle_at_right,rgba(87,181,231,0.38),transparent_34%),linear-gradient(180deg,#315B68_0%,#12252C_100%)]",
  "bg-[linear-gradient(135deg,rgba(9,32,19,0.15),rgba(9,32,19,0.74)),radial-gradient(circle_at_bottom_left,rgba(241,146,82,0.38),transparent_34%),linear-gradient(180deg,#71473A_0%,#1F1714_100%)]",
];

function formatInterestDate(value: string | null) {
  if (!value) {
    return "";
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return "";
  }

  return parsedDate.toLocaleDateString();
}

export function CompanyInterestGrid({
  interests,
  loading,
  error,
  emptyTitle,
  emptyDescription,
  cardLabel,
}: {
  interests?: CompanyInterest[];
  loading: boolean;
  error?: string | null;
  emptyTitle: string;
  emptyDescription: string;
  cardLabel: string;
}) {
  if (loading && !interests) {
    return (
      <Card>
        <p className="text-sm text-mist">Loading companies...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <p className="text-sm text-mist">{error}</p>
      </Card>
    );
  }

  if (!interests?.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {interests.map((interest, index) => {
        const company = interest.company;
        const imageUrl = resolveMediaUrl(company.company_image);
        const activityDate = formatInterestDate(interest.company_expressed_at ?? interest.corper_expressed_at);
        const companyMeta = [company.company_sector]
          .map((value) => value.trim())
          .filter(Boolean)
          .join(" · ");

        return (
          <Link key={interest.id} href={buildCorperCompanyDetailPath(company.id)} className="group block">
            <article className="flex aspect-square flex-col overflow-hidden rounded-[32px] border border-white/10 bg-white/[0.08] shadow-glow backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-lime/35">
              <div className="relative h-[75%] overflow-hidden">
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={company.company_name}
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-150"
                  />
                ) : (
                  <div
                    className={`flex h-full w-full items-center justify-center text-5xl font-semibold text-white ${fallbackPhotoBackgrounds[index % fallbackPhotoBackgrounds.length]
                      }`}
                  >
                    {getCompanyMonogram(company.company_name)}
                  </div>
                )}

                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(7,20,14,0.08)_0%,rgba(7,20,14,0.18)_35%,rgba(7,20,14,0.88)_100%)]" />
                <div className="absolute left-4 top-4 rounded-full border border-white/12 bg-[#07140E]/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                  {company.company_sector}
                </div>
                <div className="absolute right-4 top-4 rounded-full border border-white/12 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white">
                  {cardLabel}
                </div>
                <div className="absolute inset-x-4 bottom-4 flex items-end gap-3">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[20px] border border-white/12 bg-white/10 text-lg font-semibold text-white backdrop-blur-md">
                    {getCompanyMonogram(company.company_name)}
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate font-display text-2xl text-white">{company.company_name}</h2>
                  </div>
                </div>
              </div>

              <div className="flex min-h-0 flex-1 flex-col justify-end p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/88">
                  {companyMeta || "Company details pending"}
                </p>
                <p className="mt-2 truncate text-sm text-mist">{company.location}</p>
                <p className="mt-1 line-clamp-1 text-xs leading-4 text-white/80">{company.summary_description}</p>
                {activityDate ? (
                  <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-lime">
                    {activityDate}
                  </p>
                ) : null}
              </div>
            </article>
          </Link>
        );
      })}
    </div>
  );
}
