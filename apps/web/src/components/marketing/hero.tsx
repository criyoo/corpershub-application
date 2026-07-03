import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const platformStats = [
  { value: "Privacy", label: "Discovery stays structured until both sides are ready." },
  { value: "Verified", label: "Corper identity and company access points stay controlled." },
  { value: "Service", label: "Built around NYSC placement and PPA workflow realities." }
];

const workflowPanels = [
  {
    eyebrow: "Corpers",
    title: "Find safer placements",
    description: "Search company by location, sector, and functions. Company identity revealed only after contact from company.",
    className: "bg-[linear-gradient(180deg,rgba(19,146,75,0.12),rgba(19,146,75,0.04))] text-ink",
    eyebrowClassName: "text-electric"
  },
  {
    eyebrow: "Companies",
    title: "Shortlist with confidence",
    description: "Filter corps members by discipline, school, graduation year, skills, posting location and chat with corpers when ready to move forward",
    className: "bg-[linear-gradient(180deg,rgba(4,21,15,0.04),rgba(4,21,15,0.01))] text-ink",
    eyebrowClassName: "text-electric"
  },
  {
    eyebrow: "Operators",
    title: "Enable smooth experience",
    description: "Manage verifications, catalog data, billing and audit trails.",
    className: "bg-[linear-gradient(135deg,#14864A_10%,#0B5C31_60%)] text-white",
    eyebrowClassName: "text-white/80"
  }
];

export function Hero() {
  return (
    <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
      <div className="relative">
        <div className="absolute -left-8 top-8 h-32 w-32 rounded-full bg-white/10 blur-3xl" />
        <Badge tone="success">Built for the NYSC ecosystem</Badge>
        <h1 className="mt-5 font-display text-5xl leading-tight text-white md:text-6xl">
          The one stop shop for NYSC placements.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-mist">
          corpershub gives companies a structured pipeline for PPA talent and offers corpers a controlled way to discover service placements. Companies can verify profiles, express interest, and initiate conversation.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/corpers">
            <Button className="w-full sm:w-auto">Browse Corpers</Button>
          </Link>
          <Link href="/companies">
            <Button className="w-full sm:w-auto" variant="secondary">
              Browse Companies
            </Button>
          </Link>
        </div>
        <div className="mt-10 grid gap-3 sm:grid-cols-3">
          {platformStats.map((stat) => (
            <div key={stat.value} className="rounded-[24px] border border-white/10 bg-white/[0.06] p-4 backdrop-blur-xl">
              <p className="font-display text-xl text-white">{stat.value}</p>
              <p className="mt-2 text-sm text-mist">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
      <Card className="overflow-hidden border-white/10 bg-[linear-gradient(180deg,rgba(255, 255, 255, 0.81)_0%,#ECF8F0_200%)] p-0 text-ink shadow-[0_4px_40px_rgba(4,21,15,0.22)]">
        <div className="p-6 md:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="mt-3 font-display text-3xl text-white/75 leading-[1.0] text-ink">
                Confident placement, better service, smarter connections.
              </h2>
            </div>
            <div className="rounded-[28px] bg-[linear-gradient(135deg,#1FB766_0%,#118A48_70%)] px-5 py-4 text-white shadow-[0_18px_35px_rgba(17,138,72,0.22)]">
              <p className="text-[13px] uppercase tracking-[0.18em] text-white/75">NYSC</p>
              <p className="mt-0.7 font-display text-sm">National Youth Service Corps</p>
            </div>
          </div>
          <div className="mt-6 grid gap-3">
            {workflowPanels.map((panel) => (
              <div key={panel.eyebrow} className={`rounded-[24px] border border-white/10 p-5 ${panel.className}`}>
                <p className={`text-sm uppercase text-green-200 tracking-[0.18em] ${panel.eyebrowClassName}`}><b>{panel.eyebrow}</b></p>
                <h4 className="mt-3 font-display text-green-400/90 text-2xl"><b>{panel.title}</b></h4>
                <p className="mt-2 text-sm leading-6 text-white opacity-120">{panel.description}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </section>
  );
}
