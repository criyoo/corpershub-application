"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { AuthShell } from "@/components/forms/auth-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, loginWithCredentials } from "@/lib/api";
import { defaultAppPathForUser, normalizeAppPath, type SessionState } from "@/lib/session";

type LoginMode = "default" | "admin";

type ReactivationPrompt = {
  message: string;
  billingPath: string;
};

function isAllowedNextPath(path: string, role: SessionState["user"]["role"]) {
  const normalizedPath = normalizeAppPath(path);
  if (
    !normalizedPath.startsWith("/") ||
    normalizedPath.startsWith("//") ||
    normalizedPath.startsWith("/login") ||
    normalizedPath.startsWith("/admin/login")
  ) {
    return false;
  }
  if (role === "admin") {
    return normalizedPath.startsWith("/admin");
  }
  if (role === "company") {
    return normalizedPath.startsWith("/company");
  }
  if (role === "corper") {
    return normalizedPath.startsWith("/corper");
  }
  return false;
}

function getLoginContent(mode: LoginMode) {
  if (mode === "admin") {
    return {
      title: "Admin sign in",
      subtitle: "Use your admin email and password to access the corpershub workspace.",
      footer: (
        <>
          Need admin access? <Link href="/admin/register" className="text-electric">Request it here</Link>
          {" · "}
          Need the user portal? <Link href="/login/" className="text-electric">Sign in here</Link>
        </>
      ),
    };
  }

  return {
    title: "Sign in",
    subtitle: "Use your verified email and password to continue.",
    footer: (
      <>
        Don&apos;t have an account? <Link href="/register" className="text-electric">Register</Link>
      </>
    ),
  };
}

export function LoginPageContent({ mode = "default" }: { mode?: LoginMode }) {
  const router = useRouter();
  const { updateSession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [nextPath, setNextPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [reactivationPrompt, setReactivationPrompt] = useState<ReactivationPrompt | null>(null);
  const content = getLoginContent(mode);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setEmail(params.get("email") ?? "");
    setNextPath(normalizeAppPath(params.get("next")));
  }, []);

  async function handleSubmit(formData: FormData) {
    setLoading(true);
    setReactivationPrompt(null);
    try {
      const session = await loginWithCredentials({
        email: formData.get("email") as string,
        password: formData.get("password") as string,
        rememberMe: formData.get("remember_me") === "on",
      });
      updateSession(session);
      toast.success("Signed in.");
      router.push(
        isAllowedNextPath(nextPath, session.user.role)
          ? normalizeAppPath(nextPath)
          : defaultAppPathForUser(session.user)
      );
    } catch (error) {
      if (error instanceof ApiError) {
        const body = error.body as {
          code?: string;
          detail?: string;
          reactivation?: { billing_path?: string };
        };
        if (body.code === "reactivation_required" && body.reactivation?.billing_path) {
          setReactivationPrompt({
            message: body.detail ?? "Your account needs to be reactivated before you can sign in.",
            billingPath: body.reactivation.billing_path,
          });
          return;
        }
      }
      toast.error(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title={content.title}
      subtitle={content.subtitle}
      showHomeLink
      compactTopSpacing
      footer={content.footer}
    >
      <form action={handleSubmit} className="grid gap-4">
        <Input
          type="email"
          name="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email address"
          required
        />
        <Input
          type="password"
          name="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          required
        />
        <label className="inline-flex items-center gap-2 text-sm text-mist">
          <input
            type="checkbox"
            name="remember_me"
            checked={rememberMe}
            onChange={(event) => setRememberMe(event.target.checked)}
            className="h-4 w-4 rounded border-white/20 bg-white/5 text-electric focus:ring-electric"
          />
          Remember me
        </label>
        <Button disabled={loading} type="submit">
          {loading ? "Signing in..." : "Sign in"}
        </Button>
        <Link href="/forgot-password" className="text-sm text-electric">
          Forgot password?
        </Link>
        {reactivationPrompt ? (
          <Card className="border-[#F5D38C]/30 bg-[#F5D38C]/10">
            <p className="text-sm text-white">{reactivationPrompt.message}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button type="button" onClick={() => router.push(reactivationPrompt.billingPath)}>
                Yes
              </Button>
              <Button type="button" variant="secondary" onClick={() => setReactivationPrompt(null)}>
                Cancel
              </Button>
            </div>
          </Card>
        ) : null}
      </form>
    </AuthShell>
  );
}
