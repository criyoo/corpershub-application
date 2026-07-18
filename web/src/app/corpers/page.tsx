import { Suspense } from "react";

import { DiscoverCorpersPage } from "@/components/company/discover-corpers-page";

export default function PublicCorpersPage() {
  return (
    <Suspense fallback={null}>
      <DiscoverCorpersPage publicBrowse />
    </Suspense>
  );
}
