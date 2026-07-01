import type { ReactNode } from "react";

const METADATA_LINE_RE =
  /^(?:\*\*)?(?:Name|Date|NYSC Call-up Number|NYSC State Code|Company Name|Effective Date|Last Updated):(?:\*\*)?/i;
const SIGNATURE_METADATA_LINE_RE = /^(?:\*\*)?(?:Name|Date):(?:\*\*)?/i;
const SIGNATURE_NOTE_LINE_RE = /^Note:\s+Ticking the checkbox serves as electronic acceptance of this document\./i;

function renderInline(text: string) {
  const parts = text.split(/(\*\*.*?\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export function MarkdownRenderer({
  content,
  mode = "public",
}: {
  content: string;
  mode?: "public" | "signing";
}) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmedLine = line.trim();

    if (!trimmedLine) {
      index += 1;
      continue;
    }

    if (mode === "public" && SIGNATURE_NOTE_LINE_RE.test(trimmedLine)) {
      index += 1;
      continue;
    }

    if (trimmedLine === "---") {
      blocks.push(<hr key={`rule-${index}`} className="border-white/10" />);
      index += 1;
      continue;
    }

    if (trimmedLine.startsWith("# ")) {
      blocks.push(
        <h1 key={`h1-${index}`} className="font-display text-2xl text-white">
          {renderInline(trimmedLine.slice(2).trim())}
        </h1>
      );
      index += 1;
      continue;
    }

    if (trimmedLine.startsWith("## ")) {
      blocks.push(
        <h2 key={`h2-${index}`} className="font-display text-xl text-white">
          {renderInline(trimmedLine.slice(3).trim())}
        </h2>
      );
      index += 1;
      continue;
    }

    if (trimmedLine.startsWith("### ")) {
      blocks.push(
        <h3 key={`h3-${index}`} className="text-base font-semibold text-white">
          {renderInline(trimmedLine.slice(4).trim())}
        </h3>
      );
      index += 1;
      continue;
    }

    if (trimmedLine.startsWith("* ")) {
      const items: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("* ")) {
        items.push(lines[index].trim().slice(2).trim());
        index += 1;
      }

      blocks.push(
        <ul key={`list-${index}`} className="grid gap-2 pl-5 text-sm leading-7 text-mist">
          {items.map((item, itemIndex) => (
            <li key={`${item}-${itemIndex}`} className="list-disc">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    if (/^\d+\.\s+/.test(trimmedLine)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, "").trim());
        index += 1;
      }

      blocks.push(
        <ol key={`ordered-list-${index}`} className="grid gap-1 pl-5 text-sm leading-7 text-mist list-decimal">
          {items.map((item, itemIndex) => (
            <li key={`${item}-${itemIndex}`}>{renderInline(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    if (METADATA_LINE_RE.test(trimmedLine)) {
      const metadataLines: string[] = [];
      while (index < lines.length) {
        const nextLine = lines[index].trim();
        if (!nextLine || !METADATA_LINE_RE.test(nextLine)) {
          break;
        }
        metadataLines.push(nextLine);
        index += 1;
      }

      const visibleMetadataLines =
        mode === "public"
          ? metadataLines.filter((metadataLine) => !SIGNATURE_METADATA_LINE_RE.test(metadataLine))
          : metadataLines;

      if (!visibleMetadataLines.length) {
        continue;
      }

      blocks.push(
        <div key={`metadata-${index}`} className="grid gap-0 pt-2 text-sm leading-5 text-mist">
          {visibleMetadataLines.map((metadataLine, metadataIndex) => (
            <p key={`${metadataLine}-${metadataIndex}`}>{renderInline(metadataLine)}</p>
          ))}
        </div>
      );
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length) {
      const nextLine = lines[index].trim();
      if (
        !nextLine ||
        nextLine === "---" ||
        nextLine.startsWith("#") ||
        nextLine.startsWith("* ") ||
        /^\d+\.\s+/.test(nextLine)
      ) {
        break;
      }
      paragraphLines.push(nextLine);
      index += 1;
    }

    blocks.push(
      <p key={`paragraph-${index}`} className="text-sm leading-7 text-mist">
        {renderInline(paragraphLines.join(" "))}
      </p>
    );
  }

  return <div className="grid gap-4">{blocks}</div>;
}
