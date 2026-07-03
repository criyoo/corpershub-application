"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AdminVerificationAttemptDetailPage } from "@/components/dashboard/admin-verification-attempt-detail-page";

export default function AdminVerificationAttemptPage() {
  return (
    <Suspense fallback={<AdminVerificationAttemptDetailPage attemptId="" />}>
      <AdminVerificationAttemptPageContent />
    </Suspense>
  );
}

function AdminVerificationAttemptPageContent() {
  const searchParams = useSearchParams();

  return (
    <AdminVerificationAttemptDetailPage attemptId={searchParams.get("attemptId") ?? ""} />
  );
}
