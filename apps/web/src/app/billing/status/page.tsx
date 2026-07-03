import { Suspense } from "react";

import { BillingStatusPage } from "@/components/billing/billing-status-page";

export default function BillingStatusRoute() {
  return (
    <Suspense fallback={null}>
      <BillingStatusPage />
    </Suspense>
  );
}
