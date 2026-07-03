import { Suspense } from "react";

import { SubscriptionBillingPage } from "@/components/billing/subscription-billing-page";

export default function CorperBillingPage() {
  return (
    <Suspense fallback={null}>
      <SubscriptionBillingPage role="corper" />
    </Suspense>
  );
}
