"use client";

import { usePathname } from "next/navigation";

import { PublicTopBanner } from "@/components/layout/public-top-banner";
import { useAuth } from "@/components/providers/auth-provider";

export function GlobalAuthMenu() {
  const pathname = usePathname();
  const { hydrated, session } = useAuth();
  const isDashboardRoute =
    pathname.startsWith("/company/") || pathname.startsWith("/corper/") || pathname.startsWith("/admin/");

  if (pathname === "/") {
    return null;
  }

  if (isDashboardRoute) {
    return null;
  }

  if (!hydrated) {
    return null;
  }

  if (!session) {
    return (
      <>
        <div className="pointer-events-none fixed inset-x-0 top-0 z-50 px-4 py-6 md:px-8">
          <div className="pointer-events-auto mx-auto max-w-7xl">
            <PublicTopBanner />
          </div>
        </div>
        <div aria-hidden="true" className="h-[164px] md:h-[120px]" />
      </>
    );
  }

  return null;
}
