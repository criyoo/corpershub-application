import { DashboardShell } from "@/components/layout/dashboard-shell";
import { PublicEditorialPage } from "@/components/marketing/public-editorial-page";
import { loadEditorialDocument } from "@/lib/public-editorial";

export default async function CompanyHowItWorksPage() {
  const document = await loadEditorialDocument({
    relativeFilePaths: ["src/app/company/how-it-works/how.md"],
    defaultTitle: "How It Works",
    defaultIntro:
      "Corpershub makes it easier for companies to find the right corps members through a simple, transparent, and technology-driven process.",
  });

  return (
    <DashboardShell role="company" title="How It Works" hideBanner>
      <PublicEditorialPage document={document} hideTitle />
    </DashboardShell>
  );
}