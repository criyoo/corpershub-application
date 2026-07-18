import type { Metadata } from "next";

import { Card } from "@/components/ui/card";
import { SectorDetailClient } from "@/components/sectors/sector-detail-client";
import { COMPANY_SECTORS, getCompanySectorBySlug } from "@/lib/company-sectors";

export function generateStaticParams() {
  return COMPANY_SECTORS.map((sector) => ({ slug: sector.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const sector = getCompanySectorBySlug(slug);

  if (!sector) {
    return {
      title: "Sector not found | Corpershub",
    };
  }

  return {
    title: `${sector.name} | Corpershub sectors`,
    description: `Explore Corpershub company coverage for ${sector.name}.`,
  };
}

export default async function SectorDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const sector = getCompanySectorBySlug(slug);

  if (!sector) {
    return (
      <main className="min-h-screen px-4 pb-16 pt-8 md:px-8 md:pt-12">
        <div className="mx-auto max-w-3xl">
          <Card>
            <p className="text-sm text-mist">Sector not found.</p>
          </Card>
        </div>
      </main>
    );
  }

  return <SectorDetailClient sector={sector} />;
}
