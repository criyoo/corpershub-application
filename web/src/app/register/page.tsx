import Link from "next/link";

import { AuthShell } from "@/components/forms/auth-shell";

export default function RegisterPage() {
  return (
    <AuthShell
      title="Choose your registration path"
      subtitle="Create a corper or company account."
      backHref="/"
      backLabel="Home"
      compactTopSpacing
      footer={
        <>
          Already have an account? <Link href="/login/" className="text-electric"><b>Sign-in</b></Link>
        </>
      }
    >
      <div className="grid gap-4 md:grid-cols-2">
        <Link
          href="/register/corpers"
          className="rounded-[28px] border border-white/10 bg-white/[0.06] px-5 py-6 transition hover:border-lime/60 hover:bg-white/[0.1]"
        >
          <h2 className="mt-4 uppercase tracking-[0.24em] text-lime font-display text-2xl text-white">Corper</h2>
          <p className="mt-3 text-sm leading-7 text-mist">
            Browse companies profiles and express interest.
          </p>
        </Link>
        <Link
          href="/register/companies"
          className="rounded-[28px] border border-white/10 bg-white/[0.06] px-5 py-6 transition hover:border-lime/60 hover:bg-white/[0.1]"
        >
          <h2 className="mt-4 uppercase tracking-[0.24em] text-lime font-display text-2xl text-white">Company</h2>
          <p className="mt-3 text-sm leading-7 text-mist">
            Browse corpers and hire the right fit.
          </p>
        </Link>
      </div>
    </AuthShell>
  );
}
