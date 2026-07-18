"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { VerifyEmailForm } from "@/components/forms/verify-email-form";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerifyEmailForm defaultEmail="" />}>
      <VerifyEmailPageContent />
    </Suspense>
  );
}

function VerifyEmailPageContent() {
  const searchParams = useSearchParams();

  return (
    <VerifyEmailForm
      defaultEmail={searchParams.get("email") ?? ""}
    />
  );
}
