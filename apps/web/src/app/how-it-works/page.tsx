import { PublicEditorialPage } from "@/components/marketing/public-editorial-page";
import { loadEditorialDocument } from "@/lib/public-editorial";

export default async function HowItWorksPage() {
  const document = await loadEditorialDocument({
    relativeFilePaths: ["src/app/how-it-works/how.txt", "src/app/how-it-works/how.md"],
    defaultTitle: "How Corpershub Works",
    defaultIntro:
      "The Corpershub flow is designed to move users from verification through profile completion, billing, and discovery with clear access rules at each stage.",
  });

  return (
    <PublicEditorialPage
      badge="How It Works"
      document={document}
    />
  );
}
