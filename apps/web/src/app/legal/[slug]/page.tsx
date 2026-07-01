import { MarkdownRenderer } from "@/components/legal/markdown-renderer";
import { Card } from "@/components/ui/card";
import { getLegalDocumentBySlug } from "@/lib/legal-documents";
import { hydrateLegalDocumentContent, LEGAL_DOCUMENTS } from "@/lib/legal-document-template";

export function generateStaticParams() {
  return LEGAL_DOCUMENTS.map(({ slug }) => ({ slug }));
}

export default async function LegalDocumentPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const document = await getLegalDocumentBySlug(slug);

  if (!document) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(124,217,161,0.16),transparent_32%),linear-gradient(180deg,#0F2D20_0%,#07140E_100%)] px-4 py-10 sm:px-6">
        <div className="mx-auto max-w-3xl">
          <Card>
            <p className="text-sm text-mist">Legal document not found.</p>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(124,217,161,0.16),transparent_32%),linear-gradient(180deg,#0F2D20_0%,#07140E_100%)] px-4 py-10 sm:px-6">
      <div className="mx-auto grid max-w-5xl gap-6">
        <Card className="grid gap-4">
          <div className="grid gap-2">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Legal document</p>
            <h1 className="font-display text-3xl text-white">{document.title}</h1>
          </div>
          <MarkdownRenderer content={hydrateLegalDocumentContent(document.content, {})} mode="public" />
        </Card>
      </div>
    </main>
  );
}
