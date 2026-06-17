"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

type VerifyResetCodeResponse = {
  message: string;
  reset_token: string;
  email: string;
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordPageContent />
    </Suspense>
  );
}

function ResetPasswordPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resetToken = searchParams.get("token") ?? "";
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    setEmail(searchParams.get("email") ?? "");
  }, [searchParams]);

  async function handleVerifyCode(formData: FormData) {
    setVerifying(true);
    try {
      const submittedEmail = String(formData.get("email") ?? "").trim();
      const response = await apiFetch<VerifyResetCodeResponse>("/auth/reset-password/verify-code/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          email: submittedEmail,
          code: formData.get("code"),
        }),
      });
      toast.success(response.message);
      router.push(
        `/reset-password?token=${encodeURIComponent(response.reset_token)}&email=${encodeURIComponent(response.email)}`
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to verify reset code.");
    } finally {
      setVerifying(false);
    }
  }

  async function handleResetPassword(formData: FormData) {
    const submittedPassword = String(formData.get("new_password") ?? "");
    const submittedConfirmation = String(formData.get("confirm_password") ?? "");
    if (submittedPassword !== submittedConfirmation) {
      toast.error("Passwords do not match.");
      return;
    }

    setResetting(true);
    try {
      await apiFetch("/auth/reset-password/", {
        auth: false,
        method: "POST",
        body: JSON.stringify({
          reset_token: resetToken,
          new_password: submittedPassword,
        }),
      });
      toast.success("Password updated.");
      router.push(`/login/?email=${encodeURIComponent(email)}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to reset password.");
    } finally {
      setResetting(false);
    }
  }

  if (resetToken) {
    return (
      <AuthShell
        title="Create a new password"
        subtitle="Your reset code has been verified. Enter a new password to finish resetting your account."
        footer={
          <>
            Need another code? <Link href="/forgot-password" className="text-electric">Start again</Link>
          </>
        }
      >
        <form action={handleResetPassword} className="grid gap-4">
          <Input
            type="email"
            name="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email address"
            readOnly
          />
          <Input
            type="password"
            name="new_password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            placeholder="New password"
            required
          />
          <Input
            type="password"
            name="confirm_password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder="Confirm new password"
            required
          />
          <Button disabled={resetting} type="submit">
            {resetting ? "Updating..." : "Change password"}
          </Button>
        </form>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Verify reset code"
      subtitle="Enter the reset code sent to your email address before choosing a new password."
      footer={
        <>
          Need a code first? <Link href="/forgot-password" className="text-electric">Request reset code</Link>
        </>
      }
    >
      <form action={handleVerifyCode} className="grid gap-4">
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
          placeholder="6-character reset code"
          minLength={6}
          maxLength={6}
          required
        />
        <Button disabled={verifying} type="submit">
          {verifying ? "Verifying..." : "Verify reset code"}
        </Button>
      </form>
    </AuthShell>
  );
}
