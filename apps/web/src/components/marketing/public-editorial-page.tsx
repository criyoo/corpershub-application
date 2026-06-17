import { Badge } from "@/components/ui/badge";
import type { EditorialDocument } from "@/lib/public-editorial";

type PublicEditorialPageProps = {
  badge: string;
  document: EditorialDocument;
};

export function PublicEditorialPage({ badge, document }: PublicEditorialPageProps) {
  return (
    <main className="min-h-screen overflow-hidden">
      <div className="mx-auto max-w-5xl px-4 py-8 md:px-8 md:py-10">
        <section className="mx-auto max-w-4xl">
          <Badge>{badge}</Badge>
          <h1 className="mt-5 font-display text-4xl text-white md:text-5xl">{document.title}</h1>
          <p className="editorial-copy mt-5 max-w-3xl text-base leading-8 text-mist md:text-lg">{document.intro}</p>
        </section>

        {document.sections.length ? (
          <section className="mx-auto mt-10 max-w-4xl space-y-10">
            {document.sections.map((section, index) => (
              <article key={`${section.title}-${index}`}>
                <h2 className="mt-4 font-display text-2xl text-white">{section.title}</h2>
                <div className="mt-5 space-y-4">
                  {section.blocks.map((block, blockIndex) =>
                    block.type === "paragraph" ? (
                      <p key={blockIndex} className="editorial-copy text-sm leading-8 text-mist md:text-base">
                        {block.text}
                      </p>
                    ) : (
                      <ul key={blockIndex} className="grid gap-3 text-sm leading-7 text-mist md:text-base">
                        {block.items.map((item) => (
                          <li key={item} className="flex items-start gap-3">
                            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-lime" />
                            <span className="editorial-copy flex-1">{item}</span>
                          </li>
                        ))}
                        </ul>
                      )
                  )}
                </div>
              </article>
            ))}
          </section>
        ) : (
          <section className="mx-auto mt-10 max-w-4xl">
            <p className="editorial-copy text-sm leading-7 text-mist">
              Add the final write-up to the local text file for this route and the content will render here.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
