import { Suspense } from "react";

import { DiscoverCompaniesPage } from "@/components/corper/discover-companies-page";
import { Card } from "@/components/ui/card";
import { COMPANY_SECTORS, getCompanySectorBySlug } from "@/lib/company-sectors";
import {
  getNigerianStateBySlug,
  getNigerianStateSlug,
  NIGERIAN_STATES,
} from "@/lib/nigerian-reference-data";

export function generateStaticParams() {
  return COMPANY_SECTORS.flatMap((sector) =>
    NIGERIAN_STATES.map((state) => ({
      slug: sector.slug,
      state: getNigerianStateSlug(state),
    }))
  );
}

export default async function CorperSectorStateCompaniesPage({
  params,
}: {
  params: Promise<{ slug: string; state: string }>;
}) {
  const { slug, state } = await params;
  const sector = getCompanySectorBySlug(slug);
  const stateName = getNigerianStateBySlug(state);

  if (!sector || !stateName) {
    return (
      <main className="min-h-screen px-4 pb-16 pt-8 md:px-8 md:pt-12">
        <div className="mx-auto max-w-3xl">
          <Card>
            <p className="text-sm text-mist">Sector or state not found.</p>
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
        stateFilter={{
          name: stateName,
        }}
      />
    </Suspense>
  );
}
