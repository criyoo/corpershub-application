"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

type OTPResponse = {
  message: string;
};

export function VerifyEmailForm({
  defaultEmail,
}: {
  defaultEmail: string;
}) {
  const router = useRouter();
  const [email, setEmail] = useState(defaultEmail);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  async function handleVerify(_formData: FormData) {
    const normalizedEmail = email.trim();
    const normalizedCode = code.trim().toUpperCase();
    setLoading(true);
    try {
      await apiFetch("/auth/verify-email/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          email: normalizedEmail,
          code: normalizedCode,
        })
      });
      toast.success("Email verified. Your account is ready. You can sign in now.");
      router.push(`/login/?email=${encodeURIComponent(normalizedEmail)}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to verify code.");
    } finally {
      setLoading(false);
    }
  }

  async function resend() {
    if (!email.trim()) {
      toast.error("Enter your email address first.");
      return;
    }
    setResending(true);
    try {
      const response = await apiFetch<OTPResponse>("/auth/resend-otp/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({ email: email.trim() })
      });
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to resend OTP.");
    } finally {
      setResending(false);
    }
  }

  return (
    <AuthShell
      title="Verify your email"
      subtitle="Enter the 6-character alphanumeric code sent to your inbox to finish creating your account. Codes expire after 10 minutes."
      backHref="/"
      backLabel="Home"
    >
      <form action={handleVerify} className="grid gap-4">
        <Input
          type="email"
          name="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email address"
          required
        />
        <Input
          type="text"
          name="code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="6-character code"
          minLength={6}
          maxLength={6}
          required
        />
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button disabled={loading} type="submit">
            {loading ? "Verifying..." : "Verify email"}
          </Button>
          <Button disabled={resending} type="button" variant="secondary" onClick={() => void resend()}>
            {resending ? "Resending..." : "Resend OTP"}
          </Button>
        </div>
      </form>
    </AuthShell>
  );
}
