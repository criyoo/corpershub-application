"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiFetch } from "@/lib/api";

type AdminRegisterResponse = {
  status: string;
  message: string;
  email: string;
};

export default function AdminRegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  async function handleSubmit(formData: FormData) {
    const emailVal = String(formData.get("email") ?? "").trim();
    const passwordVal = String(formData.get("password") ?? "");
    const confirmVal = String(formData.get("confirm_password") ?? "");

    if (passwordVal !== confirmVal) {
      toast.error("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const response = await apiFetch<AdminRegisterResponse>("/auth/admin/register/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          email: emailVal,
          password: passwordVal,
        }),
      });

      if (response.status === "otp_sent") {
        setEmail(emailVal);
        setSubmitted(true);
        toast.success(response.message);
        router.push(`/admin/verify-email?email=${encodeURIComponent(emailVal)}`);
        return;
      }

      toast.success(response.message);
    } catch (error) {
      if (error instanceof ApiError) {
        const body = error.body as Record<string, string[]>;
        const message = Object.values(body).flat()[0] ?? error.message;
        toast.error(message);
      } else {
        toast.error(error instanceof Error ? error.message : "Unable to submit admin registration request.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Admin access registration"
      subtitle="Submit your admin access request. An existing admin will review and approve your account."
      backHref="/admin"
      backLabel="Back to admin home"
      compactTopSpacing
      footer={
        <>
          Already have an admin account? <Link href="/admin/login" className="text-electric"><b>Sign in</b></Link>
        </>
      }
    >
      <div className="grid gap-4">
        <Card className="border-white/10 bg-white/[0.05] p-5">
          <p className="text-xs uppercase tracking-[0.22em] text-lime">How it works</p>
          <p className="mt-3 text-sm leading-7 text-mist">
            Enter your email and password below. We will send a verification code to your email. After verification, an existing admin will review your request.
          </p>
        </Card>

        <form action={handleSubmit} className="grid gap-4">
          <Input
            type="email"
            name="email"
            placeholder="Admin email address"
            required
          />
          <Input
            type="password"
            name="password"
            placeholder="Create a password"
            required
          />
          <Input
            type="password"
            name="confirm_password"
            placeholder="Confirm password"
            required
          />
          <Button disabled={loading} type="submit">
            {loading ? "Submitting..." : "Create account"}
          </Button>
        </form>
      </div>
    </AuthShell>
  );
}
