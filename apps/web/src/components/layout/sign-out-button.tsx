"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

type SignOutButtonProps = {
  className?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  plain?: boolean;
  label?: string;
};

export function SignOutButton({
  className,
  variant = "secondary",
  plain = false,
  label = "Logout",
}: SignOutButtonProps) {
  const { hydrated, session, logout } = useAuth();

  if (!hydrated || !session) {
    return null;
  }

  async function handleSignOut() {
    try {
      await apiFetch<{ message: string }>("/auth/logout/", {
        method: "POST",
      });
    } catch {
      // Clear the local session even if the logout request fails or the token is already stale.
    } finally {
      logout();
      window.location.replace("/");
    }
  }

  if (plain) {
    return (
      <button type="button" onClick={() => void handleSignOut()} className={className}>
        {label}
      </button>
    );
  }

  return (
    <Button type="button" variant={variant} className={className} onClick={() => void handleSignOut()}>
      {label}
    </Button>
  );
}
