"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function CompanyBillingPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/company/dashboard");
  }, [router]);

  return null;
}
