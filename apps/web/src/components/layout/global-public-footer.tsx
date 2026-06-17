"use client";

import { usePathname } from "next/navigation";

import { PublicFooter } from "@/components/layout/public-footer";

const hiddenRoutePrefixes = ["/admin/", "/company/", "/corper/"];

export function GlobalPublicFooter() {
  const pathname = usePathname();
  const isDashboardRoute = hiddenRoutePrefixes.some((prefix) => pathname.startsWith(prefix));

  if (isDashboardRoute) {
    return null;
  }

  return <PublicFooter />;
}
