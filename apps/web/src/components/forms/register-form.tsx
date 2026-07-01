"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { PpaDisclaimerNote } from "@/components/legal/ppa-disclaimer-note";
import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, apiFetch } from "@/lib/api";

type RegisterRole = "corper" | "company";

type RegisterResponse = {
  email: string;
  role: RegisterRole;
  message: string;
};

const roleContent = {
  corper: {
    title: "Create corper account",
    subtitle: "Register with your email and password. We will send an OTP to verify your email.",
    emailPlaceholder: "Email address",
    switchHref: "/register/companies",
    switchLabel: "Register",
    switchPrompt: "Need to register as company?",
  },
  company: {
    title: "Create company account",
    subtitle: "Register as a company to view corper details.",
    emailPlaceholder: "Work email",
    switchHref: "/register/corpers",
    switchLabel: "Register",
    switchPrompt: "Need to register as a corper?",
  },
} satisfies Record<
  RegisterRole,
  {
    title: string;
    subtitle: string;
    emailPlaceholder: string;
    switchHref: string;
    switchLabel: string;
    switchPrompt: string;
  }
>;

function resolveApiErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError && error.body && typeof error.body === "object") {
    for (const value of Object.values(error.body as Record<string, unknown>)) {
      if (Array.isArray(value) && typeof value[0] === "string") {
        return value[0];
      }
      if (typeof value === "string") {
        return value;
      }
    }
  }
  return error instanceof Error ? error.message : fallback;
}

export function RegisterForm({
  role,
  backHref,
  backLabel,
}: {
  role: RegisterRole;
  backHref?: string;
  backLabel?: string;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const content = roleContent[role];

  async function handleSubmit(formData: FormData) {
    setLoading(true);
    try {
      const email = String(formData.get("email") ?? "");
      const response = await apiFetch<RegisterResponse>("/auth/register/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          email,
          password: formData.get("password"),
          role,
        }),
      });
      toast.success(response.message);
      router.push(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (error) {
      toast.error(resolveApiErrorMessage(error, "Unable to register."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title={content.title}
      subtitle={content.subtitle}
      showHomeLink={!backHref}
      backHref={backHref}
      backLabel={backLabel}
      compactTopSpacing
      footer={
        <>
          Already have an account? <Link href="/login/" className="text-electric"><b>Sign in</b></Link>
          {" · "}
          {content.switchPrompt} <Link href={content.switchHref} className="text-electric"><b>{content.switchLabel}</b></Link>
        </>
      }
    >
      <form action={handleSubmit} className="grid gap-4">
        <Input type="email" name="email" placeholder={content.emailPlaceholder} required />
        <Input type="password" name="password" placeholder="Create a password" required />
        <Button disabled={loading} type="submit">
          {loading ? "Sending OTP..." : "Continue"}
        </Button>
        <PpaDisclaimerNote />
      </form>
    </AuthShell>
  );
}
