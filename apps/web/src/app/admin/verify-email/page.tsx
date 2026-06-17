"use client";

import { Suspense, useState } from "react";

import { VerifyEmailForm } from "@/components/auth/verify-email-form";

function LoadingState() {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");

  return (
    <div className="grid gap-4">
      <div className="h-10 w-full rounded-2xl bg-white/10" />
      <div className="h-10 w-full rounded-2xl bg-white/10" />
      <div className="h-10 w-24 rounded-full bg-white/10" />
    </div>
  );
}

export default function AdminVerifyEmailPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <VerifyEmailForm />
    </Suspense>
  );
}
