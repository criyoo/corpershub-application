import { Suspense } from "react";

import { DiscoverCompaniesPage } from "@/components/corper/discover-companies-page";

export default function CorperCompaniesPage() {
  return (
    <Suspense fallback={null}>
      <DiscoverCompaniesPage />
    </Suspense>
  );
}
