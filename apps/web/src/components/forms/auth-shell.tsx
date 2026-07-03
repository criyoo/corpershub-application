import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { Card } from "@/components/ui/card";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  showHomeLink = false,
  backHref,
  backLabel = "Back",
  compactTopSpacing = false,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  showHomeLink?: boolean;
  backHref?: string;
  backLabel?: string;
  compactTopSpacing?: boolean;
}) {
  const topLink =
    backHref && !(backHref === "/" && backLabel === "Home")
      ? { href: backHref, label: backLabel }
      : null;

  return (
    <main
      className={`flex min-h-screen px-4 ${compactTopSpacing ? "justify-center pt-5 pb-10 md:pt-6" : "items-center justify-center py-10"
        }`}
    >
      <div className="w-full max-w-xl">
        {topLink ? (
          <Link
            href={topLink.href}
            className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm font-medium text-[#c3c8cf] transition hover:border-lime/70 hover:bg-white/[0.12] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            {topLink.label}
          </Link>
        ) : null}
        <Card className="border-white/10 bg-white/[0.08]">
          <Link href="/" className="text-sm uppercase tracking-[0.24em] text-lime">
            corpershub
          </Link>
          <h1 className="mt-5 font-display text-3xl text-white">{title}</h1>
          <p className="mt-3 text-sm text-mist">{subtitle}</p>
          <div className="mt-8">{children}</div>
          {footer ? <div className="mt-6 text-sm text-mist">{footer}</div> : null}
        </Card>
      </div>
    </main>
  );
}
