import { Suspense } from "react";

import { DiscoverCompaniesPage } from "@/components/corper/discover-companies-page";

export default function PublicCompaniesPage() {
  return (
    <Suspense fallback={null}>
      <DiscoverCompaniesPage publicBrowse />
    </Suspense>
  );
}
