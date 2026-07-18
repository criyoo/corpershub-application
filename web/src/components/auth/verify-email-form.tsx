"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

export function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const defaultEmail = searchParams.get("email") ?? "";
  const [email, setEmail] = useState(defaultEmail);
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  async function handleVerify(_formData: FormData) {
    setLoading(true);
    try {
      await apiFetch("/auth/admin/register/verify/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          code: code.trim().toUpperCase(),
        }),
      });
      toast.success("Admin access request submitted. An existing admin will review your request.");
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
      await apiFetch("/auth/resend-otp/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({ email: email.trim() }),
      });
      toast.success("A new verification code has been sent.");
    } catch {
      toast.error("Unable to resend code.");
    } finally {
      setResending(false);
    }
  }

  return (
    <AuthShell
      title="Verify your email"
      subtitle="Enter the 6-character code sent to your inbox to verify your admin registration request. Codes expire after 10 minutes."
      backHref="/admin/register"
      backLabel="Back to registration"
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
            {loading ? "Verifying..." : "Submit"}
          </Button>
          <Button disabled={resending} type="button" variant="secondary" onClick={() => void resend()}>
            {resending ? "Resending..." : "Resend code"}
          </Button>
        </div>
      </form>
    </AuthShell>
  );
}
