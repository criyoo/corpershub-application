import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const plans = [
  {
    name: "7 Days Free Trial",
    price: "Free",
    description: "Corpers can browse companies for 7 days, but match score, interest, and chat stay locked.",
    features: ["7-day free browsing access", "Full dashboard access", "See full profile", "Notifications"]
  },
  {
    name: "Corper Paid Plans",
    price: "₦10,000  -  ₦18,000  -  ₦30,000",
    description: "Paid corper access is available in 3, 6, and 12 month packages.",
    features: ["Full access the duration", "Company/Corper match scores", "Send interest", "Realtime chat"]
  }
];

export default function PricingPage() {
  return (
    <main className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-6xl">
        <Badge tone="success">Choose trial or paid access before signup.</Badge>
        <h1 className="mt-4 font-display text-5xl text-white">NYSC placement plans.</h1>
        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {plans.map((plan) => (
            <Card key={plan.name} className={plan.name === "Paid" ? "border-lime/40 bg-white/[0.1]" : undefined}>
              <p className="text-sm uppercase tracking-[0.22em] text-lime">{plan.name}</p>
              <h2 className="mt-4 font-display text-3xl text-white">{plan.price}</h2>
              <p className="mt-4 text-sm text-mist">{plan.description}</p>
              <ul className="mt-5 space-y-2 text-xs text-lime">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
        <div className="mt-8">
          <Link href="/register">
            <Button>Create account</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
