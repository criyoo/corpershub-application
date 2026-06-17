import { Suspense } from "react";

import { DiscoverCorpersPage } from "@/components/company/discover-corpers-page";

export default function CompanyCorpersPage() {
  return (
    <Suspense fallback={null}>
      <DiscoverCorpersPage />
    </Suspense>
  );
}
