import { DashboardShell } from "@/components/layout/dashboard-shell";
import { PublicEditorialPage } from "@/components/marketing/public-editorial-page";
import { loadEditorialDocument } from "@/lib/public-editorial";

export default async function CorperHowItWorksPage() {
  const document = await loadEditorialDocument({
    relativeFilePaths: ["src/app/corper/how-it-works/how.md"],
    defaultTitle: "How It Works",
    defaultIntro: "",
  });

  return (
    <DashboardShell role="corper" title="How It Works" hideBanner>
      <PublicEditorialPage document={document} hideTitle />
    </DashboardShell>
  );
}