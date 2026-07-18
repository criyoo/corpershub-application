import Image from "next/image";
import Link from "next/link";
import type { Metadata } from "next";

import { BackButton } from "@/components/navigation/back-button";
import { COMPANY_SECTORS } from "@/lib/company-sectors";

export const metadata: Metadata = {
  title: "Sectors | Corpershub",
  description: "Explore the company sectors available on Corpershub.",
};

export default function SectorsPage() {
  return (
    <main className="min-h-screen px-4 pb-16 pt-8 md:px-8 md:pt-12">
      <section className="mx-auto max-w-7xl">
        <BackButton />

        <div className="mt-8 max-w-3xl">
          <p className="text-sm uppercase tracking-[0.26em] text-lime">Sectors</p>
          <h1 className="mt-4 font-display text-4xl text-white">Sectors with PPA opportunities</h1>
          <p className="mt-4 text-base leading-7 text-mist md:text-lg">
            Explore sectors with PPA opportunities and matching preferences.
          </p>
        </div>

        <div className="mt-10 grid gap-x-5 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
          {COMPANY_SECTORS.map((sector, index) => (
            <article key={sector.name} className="min-w-0">
              <Link
                href={`/sectors/${sector.slug}`}
                aria-label={`View ${sector.name} sector details`}
                className="group block"
              >
                <div className="relative aspect-square overflow-hidden rounded-[24px] border border-white/10 bg-white/[0.07] shadow-glow transition duration-300 group-hover:-translate-y-1 group-hover:border-lime/50">
                  <Image
                    src={sector.imageSrc}
                    alt={sector.name}
                    fill
                    sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                    priority={index < 4}
                    className="object-cover transition duration-500 group-hover:scale-105"
                  />
                </div>
                <h2 className="mt-3 text-center text-base font-semibold leading-6 text-white">
                  {sector.name}
                </h2>
              </Link>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
