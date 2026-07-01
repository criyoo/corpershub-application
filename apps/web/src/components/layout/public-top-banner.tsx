"use client";

import Link from "next/link";

import { TopStatusNav } from "@/components/layout/top-status-nav";

export function PublicTopBanner() {
  return (
    <header className="flex flex-col gap-4 rounded-[30px] border border-white/10 bg-white/[0.08] px-6 py-5 backdrop-blur-xl md:flex-row md:items-center md:justify-between">
      <Link href="/" className="inline-flex items-center gap-3">
        <img
          src="/images/corpershub-logo.jpeg"
          alt="corpershub"
          className="h-16 w-16 rounded-full object-cover"
        />
        <span className="font-display text-xl font-semibold tracking-[0.01em] text-white md:text-xl">
          Corpershub
        </span>
      </Link>
      <TopStatusNav />
    </header>
  );
}
