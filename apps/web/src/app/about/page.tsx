import { PublicEditorialPage } from "@/components/marketing/public-editorial-page";
import { loadEditorialDocument } from "@/lib/public-editorial";

export default async function AboutPage() {
  const document = await loadEditorialDocument({
    relativeFilePaths: ["src/app/about/about.txt", "src/app/about/about.md"],
    defaultTitle: "About Corpershub",
    defaultIntro:
      "Corpershub connects corpers and companies through a structured onboarding, verification, and discovery flow designed for trust, privacy, and better PPA placement outcomes.",
  });

  return (
    <PublicEditorialPage
      badge="About"
      document={document}
    />
  );
}
