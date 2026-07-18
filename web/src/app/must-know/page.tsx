import { PublicEditorialPage } from "@/components/marketing/public-editorial-page";
import { loadEditorialDocument } from "@/lib/public-editorial";

export default async function MustKnowPage() {
  const document = await loadEditorialDocument({
    relativeFilePaths: ["src/app/must-know/must-know.md"],
    defaultTitle: "Corpers Must-Know",
    defaultIntro:
      "Everything you need to know about the NYSC programme, from mobilization to passing out.",
  });

  return (
    <PublicEditorialPage
      badge="Must-Know"
      document={document}
    />
  );
}