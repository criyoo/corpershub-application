"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSubmit(formData: FormData) {
    setLoading(true);
    try {
      const email = String(formData.get("email") ?? "").trim();
      await apiFetch("/auth/forgot-password/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({ email })
      });
      toast.success("If the account exists, a reset code has been sent.");
      router.push(`/reset-password?email=${encodeURIComponent(email)}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to send reset code.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Forgot password"
      subtitle="Request a reset code for your account."
    >
      <form action={handleSubmit} className="grid gap-4">
        <Input type="email" name="email" placeholder="Email address" required />
        <Button disabled={loading} type="submit">
          {loading ? "Sending..." : "Send reset code"}
        </Button>
      </form>
    </AuthShell>
  );
}
