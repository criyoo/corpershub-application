"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SignOutButton } from "@/components/layout/sign-out-button";
import { useAuth } from "@/components/providers/auth-provider";
import type { SessionUser } from "@/lib/session";

const baseLinkClass =
  "inline-flex items-center justify-center rounded-full border px-4 py-2 text-sm font-semibold transition-[transform,background-color,color,border-color,box-shadow] duration-300 ease-out will-change-transform hover:scale-[0.97] active:scale-[0.94]";
const primaryLinkClass =
  "border-white/12 bg-white/[0.08] text-white shadow-[0_10px_24px_rgba(7,20,14,0.12)] hover:border-lime/70 hover:bg-lime hover:text-[#0B261B] hover:shadow-[0_18px_32px_rgba(194,255,119,0.24)]";
const secondaryLinkClass =
  "border-white/12 bg-white/[0.08] text-white shadow-[0_10px_24px_rgba(7,20,14,0.12)] hover:border-[#9ED9FF] hover:bg-[#9ED9FF] hover:text-[#0B261B] hover:shadow-[0_18px_32px_rgba(158,217,255,0.24)]";
const accentLinkClass =
  "border-transparent bg-white/[0.08] text-white shadow-[0_10px_24px_rgba(7,20,14,0.12)] hover:bg-[#F5D38C] hover:text-[#0B261B] hover:shadow-[0_18px_32px_rgba(245,211,140,0.24)]";
const dangerLinkClass =
  "border-white/12 bg-white/[0.08] text-white shadow-[0_10px_24px_rgba(7,20,14,0.12)] hover:border-[#FCA5A5] hover:bg-[#FCA5A5] hover:text-[#0B261B] hover:shadow-[0_18px_32px_rgba(252,165,165,0.24)]";
const activeLinkClass = "border-lime/70 bg-lime text-[#0B261B] shadow-[0_18px_32px_rgba(194,255,119,0.24)]";

function resolveDashboardHref(user: SessionUser) {
  if (user.role === "company") {
    return "/company/dashboard";
  }
  if (user.role === "corper") {
    return "/corper/dashboard";
  }
  return "/admin/overview";
}

function normalizePath(path: string) {
  if (path === "/") {
    return path;
  }
  return path.replace(/\/+$/, "");
}

function isActivePath(pathname: string, href: string) {
  const currentPath = normalizePath(pathname);
  const targetPath = normalizePath(href);

  if (targetPath === "/") {
    return currentPath === targetPath;
  }

  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`);
}

function resolveLinkClass(pathname: string, href: string, variant: "primary" | "secondary" | "accent" | "danger") {
  if (isActivePath(pathname, href)) {
    return `${baseLinkClass} ${activeLinkClass}`;
  }

  if (variant === "secondary") {
    return `${baseLinkClass} ${secondaryLinkClass}`;
  }
  if (variant === "accent") {
    return `${baseLinkClass} ${accentLinkClass}`;
  }
  if (variant === "danger") {
    return `${baseLinkClass} ${dangerLinkClass}`;
  }
  return `${baseLinkClass} ${primaryLinkClass}`;
}

export function TopStatusNav({ className = "" }: { className?: string }) {
  const pathname = usePathname();
  const { hydrated, session } = useAuth();

  if (!hydrated) {
    return null;
  }

  if (session) {
    const dashboardHref = resolveDashboardHref(session.user);

    return (
      <nav className={`flex flex-wrap items-center justify-center gap-3 ${className}`}>
        <Link className={resolveLinkClass(pathname, "/", "primary")} href="/">
          Home
        </Link>
        <Link className={resolveLinkClass(pathname, dashboardHref, "secondary")} href={dashboardHref}>
          Dashboard
        </Link>
        <SignOutButton plain className={resolveLinkClass(pathname, "#logout", "danger")} label="Logout" />
      </nav>
    );
  }

  return (
    <nav className={`flex flex-wrap items-center justify-center gap-3 ${className}`}>
      <Link className={resolveLinkClass(pathname, "/about", "secondary")} href="/about">
        About
      </Link>
      <Link className={resolveLinkClass(pathname, "/how-it-works", "secondary")} href="/how-it-works">
        How It Works
      </Link>
      <Link className={resolveLinkClass(pathname, "/corpers", "primary")} href="/corpers">
        Corpers
      </Link>
      <Link className={resolveLinkClass(pathname, "/companies", "secondary")} href="/companies">
        Companies
      </Link>
      <Link className={resolveLinkClass(pathname, "/login", "accent")} href="/login/">
        Sign in
      </Link>
      <Link className={resolveLinkClass(pathname, "/register", "primary")} href="/register">
        Register
      </Link>
    </nav>
  );
}
