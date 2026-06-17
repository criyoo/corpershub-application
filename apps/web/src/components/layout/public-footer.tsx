"use client";

import { ArrowRight, Mail, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

const footerSections = [
  {
    title: "Explore",
    links: [
      { label: "Home", href: "/" },
      { label: "About", href: "/about" },
      { label: "How it works", href: "/how-it-works" },
      { label: "Pricing", href: "/pricing" },
      { label: "Companies", href: "/companies" },
      { label: "Corpers", href: "/corpers" },
    ],
  },
  {
    title: "Get Started",
    links: [
      { label: "Corper signup", href: "/register/corpers" },
      { label: "Company signup", href: "/register/companies" },
      { label: "Sign in", href: "/login/" },
      { label: "Create account", href: "/register" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy policy", href: "/legal/privacy-policy" },
      { label: "Terms of use", href: "/legal/terms-of-service" },
      { label: "Cookie policy", href: "/legal/cookies-policy" },
      { label: "Trust & safety", href: "/legal/acceptable-use-policy" },
    ],
  },
];

const socialLinks = [
  { label: "Facebook", icon: "/images/facebook.webp", href: "#" },
  { label: "Instagram", icon: "/images/instagram.webp", href: "#" },
  { label: "X", icon: "/images/X.webp", href: "#" },
  { label: "LinkedIn", icon: "/images/linkedin.webp", href: "https://www.linkedin.com/company/corpers-hub/" },
  { label: "YouTube", icon: "/images/youtube.webp", href: "#" },
  { label: "TikTok", icon: "/images/tictok.webp", href: "#" },
  { label: "Threads", icon: "/images/threads.webp", href: "#" },
  { label: "Telegram", icon: "/images/telegram.webp", href: "#" },
  { label: "WhatsApp", icon: "/images/whatsapp.webp", href: "#" },
];

export function PublicFooter() {
  const [comingSoonLabel, setComingSoonLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!comingSoonLabel) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setComingSoonLabel(null);
    }, 2200);

    return () => window.clearTimeout(timeoutId);
  }, [comingSoonLabel]);

  return (
    <footer className="relative overflow-hidden border-t border-white/10 bg-[#06120D]">
      <div className="absolute -right-24 top-10 h-56 w-56 rounded-full bg-lime/10 blur-[3.2rem]" />
      <div className="absolute -left-20 bottom-0 h-48 w-48 rounded-full bg-white/10 blur-[3.2rem]" />

      <div className="relative mx-auto grid max-w-7xl gap-6 px-4 py-12 md:px-8 lg:grid-cols-[1.15fr_1.6fr]">
        <div className="flex h-full flex-col">
          <Link href="/" className="inline-flex w-fit items-center gap-3">
            <img
              src="/images/corpershub-logo.jpeg"
              alt="corpershub"
              className="rounded-full border border-white/15 object-cover h-16 w-16 mt-4"
            />
            <span className="font-display text-2xl font-semibold text-white">Corpershub</span>
          </Link>
          <div className="mt-12">
            <p className="max-w-md font-display text-2xl font-semibold leading-tight text-white">
              Trusted NYSC PPA placement discovery for corpers and companies.
            </p>
            <br />
            <p className="max-w-md text-sm leading-2 text-mist">
              Clear profiles, verified access, smarter matching, and a safer way to find the right PPA connection.
            </p>
            <br />
          </div>
          <div className="mt-24">
            <form action="/companies" className="flex max-w-md items-center overflow-hidden rounded-3xl border border-white/10 bg-white/[0.05] px-3 h-20">
              <label htmlFor="footer-search" className="sr-only">
                Search companies
              </label>
              <div className="flex flex-1 items-center gap-2 px-4">
                <span className="h-1 w-1 rounded-full bg-lime" aria-hidden="true" />
                <input
                  id="footer-search"
                  name="search"
                  placeholder="Search companies, sectors, or roles"
                  className="min-w-0 flex-1 bg-transparent py-4 text-[16px] text-white outline-none placeholder:text-[grey]"
                />
              </div>
              <button
                type="submit"
                className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-lime text-[#06120D] transition hover:scale-105 hover:bg-white"
                aria-label="Search"
              >
                <ArrowRight className="h-8 w-8" />
              </button>
            </form>
          </div>
        </div>

        <div className="flex h-full flex-col gap-8">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-lime mb-2">Social</p>
            <div className="flex flex-wrap gap-2">
              {socialLinks.map((link) => (
                link.label === "LinkedIn" ? (
                  <a
                    key={link.label}
                    href={link.href}
                    aria-label={link.label}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border border-[#07140E] bg-[#06120D] transition hover:-translate-y-0.5 hover:border-lime/40"
                  >
                    <img src={link.icon} alt="" className="h-full w-full scale-110 object-cover" />
                  </a>
                ) : (
                  <button
                    key={link.label}
                    type="button"
                    aria-label={link.label}
                    onClick={() => setComingSoonLabel(link.label)}
                    className="inline-flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border border-[#07140E] bg-[#06120D] transition hover:-translate-y-0.5 hover:border-lime/40"
                  >
                    <img src={link.icon} alt="" className="h-full w-full scale-110 object-cover" />
                  </button>
                )
              ))}
            </div>
            <div
              aria-live="polite"
              className={`max-w-xs rounded-2xl border border-lime/20 bg-[linear-gradient(135deg,rgba(190,227,202,0.18),rgba(6,18,13,0.95))] p-2 shadow-[0_18px_45px_rgba(0,0,0,0.28)] transition-all duration-300 ${comingSoonLabel ? "translate-y-0 opacity-100" : "pointer-events-none -translate-y-1 opacity-0"
                }`}
            >
              <div className="flex items-start gap-3">
                <span className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-lime text-[#06120D]">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">Coming Soon</p>
                  <p className="mt-1 text-xs leading-5 text-mist">
                    {comingSoonLabel ? `${comingSoonLabel} will be available soon.` : " "}
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div className="grid gap-6 sm:grid-cols-3">
            {footerSections.map((section) => (
              <nav key={section.title} aria-label={section.title}>
                <h2 className="text-xs font-semibold uppercase tracking-[0.22em] text-lime">{section.title}</h2>
                <ul className="mt-4 grid gap-3 text-sm text-mist">
                  {section.links.map((link) => (
                    <li key={link.label}>
                      <Link className="transition hover:text-white" href={link.href}>
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>

          <div className="mt-[-0.2]">
            <div className="grid gap-4 rounded-[24px] border border-white/10 bg-white/[0.05] p-5 md:grid-cols-2">
              <a className="group flex items-center gap-3 text-sm text-mist transition hover:text-white" href="mailto:info@corpershub.ng">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-lime/15 text-lime transition group-hover:bg-lime group-hover:text-[#06120D]">
                  <Mail className="h-4 w-4" />
                </span>
                info@corpershub.ng
              </a>
              <div className="flex items-center gap-3 text-sm text-mist">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-lime/15 text-lime">
                  CH
                </span>
                PPA placements redefined
              </div>
            </div>

            <p className="text-sm leading-9 text-lime mt-10">
              Copyright {new Date().getFullYear()} Corpershub. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer >
  );
}
