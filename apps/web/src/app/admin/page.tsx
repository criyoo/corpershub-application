"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AdminIndexPage() {
  const pathname = usePathname();

  if (pathname === "/admin" || pathname === "/admin/") {
    return (
      <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(124,217,161,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,255,255,0.1),_transparent_18%),linear-gradient(180deg,_#134B35_0%,_#0B261B_58%,_#07140E_100%)]">
        <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col items-center justify-center px-4 py-12">
          <div className="w-full max-w-2xl">
            <div className="mb-12 text-center">
              <Link
                href="/"
                className="inline-flex items-center justify-center rounded-full border border-lime/80 bg-lime/10 px-8 py-3 font-display text-2xl font-bold text-[#E6D28C] shadow-[0_0_0_1px_rgba(194,255,119,0.08),0_14px_30px_rgba(7,20,14,0.18)] transition hover:bg-lime hover:text-[#E6D28C]"
              >
                corpershub Home
              </Link>
              <h1 className="mt-8 font-display text-4xl text-white">Admin Workspace</h1>
              <p className="mt-4 text-lg leading-7 text-mist">
                Manage users, verifications, payments, and platform configuration.<br />
                Sign in to your admin account or request access.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Link
                href="/admin/login"
                className="group rounded-3xl border border-white/10 bg-white/[0.06] p-8 transition duration-200 hover:border-lime/50 hover:bg-white/[0.09]"
              >
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Existing admin</p>
                <p className="mt-3 font-display text-2xl text-white">Sign in</p>
                <p className="mt-3 text-xs leading-6 text-mist">
                  Access the admin dashboard with your existing admin credentials.
                </p>
                <span className="mt-6 inline-flex rounded-full border border-lime/30 bg-lime/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-lime transition group-hover:bg-lime/20">
                  Login
                </span>
              </Link>

              <Link
                href="/admin/register"
                className="group rounded-3xl border border-white/10 bg-white/[0.06] p-8 transition duration-200 hover:border-lime/50 hover:bg-white/[0.09]"
              >
                <p className="text-xs uppercase tracking-[0.22em] text-lime">New admin</p>
                <p className="mt-3 font-display text-2xl text-white">Request access</p>
                <p className="mt-3 text-xs leading-6 text-mist">
                  Submit an admin access request.<br />
                  An existing admin will review and approve.
                </p>
                <span className="mt-6 inline-flex rounded-full border border-lime/30 bg-lime/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-lime transition group-hover:bg-lime/20">
                  Register
                </span>
              </Link>
            </div>

            <p className="mt-12 text-center text-sm text-mist">
              Need the user portal?{" "}
              <Link href="/login/" className="text-electric">
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
