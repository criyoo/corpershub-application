import { PublicTopBanner } from "@/components/layout/public-top-banner";
import { HomeBackgroundSlideshow } from "@/components/marketing/home-background-slideshow";
import { Hero } from "@/components/marketing/hero";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const privacyPoints = [
  "Company registration rejects free email domains unless allowlisted.",
  "Company contact details remain private until connection is established.",
  "Sensitive corper identifiers stay masked in UI payloads.",
  "Realtime chat opens only after a company initiates a conversation."
];

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,_#134B35_0%,_#0B261B_58%,_#07140E_100%)]">
      <div className="absolute inset-0">
        <HomeBackgroundSlideshow />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(7,20,14,0.78)_0%,rgba(19,75,53,0.62)_38%,rgba(7,20,14,0.88)_100%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(124,217,161,0.22),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,255,255,0.12),_transparent_16%),linear-gradient(180deg,rgba(255,255,255,0.04)_0%,rgba(7,20,14,0.14)_100%)]" />
      </div>
      <div className="relative z-10 mx-auto max-w-7xl px-4 py-6 md:px-8">
        <PublicTopBanner />

        <div className="mt-12">
          <Hero />
        </div>

        <section className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {privacyPoints.map((description) => (
            <Card key={description}>
              <Badge>Privacy rule</Badge>
              <p className="mt-4 text-xs text-white">{description}</p>
            </Card>
          ))}
        </section>
      </div>
    </main>
  );
}
