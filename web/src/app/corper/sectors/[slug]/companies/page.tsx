import { Suspense } from "react";

import { DiscoverCompaniesPage } from "@/components/corper/discover-companies-page";
import { Card } from "@/components/ui/card";
import { COMPANY_SECTORS, getCompanySectorBySlug } from "@/lib/company-sectors";

export function generateStaticParams() {
  return COMPANY_SECTORS.map((sector) => ({ slug: sector.slug }));
}

export default async function CorperSectorCompaniesPage({
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

  return (
    <Suspense fallback={null}>
      <DiscoverCompaniesPage
        sectorFilter={{
          name: sector.name,
          backHref: `/sectors/${sector.slug}`,
          backLabel: "Back to sector",
        }}
      />
    </Suspense>
  );
}
