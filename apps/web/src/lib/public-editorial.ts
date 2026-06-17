import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";

export type EditorialBlock =
  | {
      type: "paragraph";
      text: string;
    }
  | {
      type: "list";
      items: string[];
    };

export type EditorialSection = {
  title: string;
  blocks: EditorialBlock[];
};

export type EditorialDocument = {
  title: string;
  intro: string;
  sections: EditorialSection[];
  isEmpty: boolean;
};

type LoadEditorialDocumentOptions = {
  relativeFilePath?: string;
  relativeFilePaths?: string[];
  defaultTitle: string;
  defaultIntro: string;
};

function resolveWebAppRoot() {
  const cwd = process.cwd();

  if (existsSync(path.join(cwd, "src", "app"))) {
    return cwd;
  }

  if (existsSync(path.join(cwd, "apps", "web", "src", "app"))) {
    return path.join(cwd, "apps", "web");
  }

  return cwd;
}

function normalizeText(value: string) {
  return value.replace(/\r\n/g, "\n").trim();
}

function isListLine(line: string) {
  return /^([-*]|\d+\.)\s+/.test(line);
}

function cleanListLine(line: string) {
  return line.replace(/^([-*]|\d+\.)\s+/, "").trim();
}

function cleanHeading(line: string) {
  return line.replace(/^#{1,6}\s+/, "").replace(/:\s*$/, "").trim();
}

function isMarkdownHeading(line: string) {
  return /^#{1,6}\s+/.test(line);
}

function looksLikeHeading(line: string) {
  if (!line) {
    return false;
  }
  if (isMarkdownHeading(line)) {
    return true;
  }
  if (line.length > 80) {
    return false;
  }
  if (/[.!?]$/.test(line)) {
    return false;
  }
  return /^[A-Z0-9][A-Za-z0-9,&'()/ -]*$/.test(line) || /:\s*$/.test(line);
}

function createBlocks(rawText: string): EditorialBlock[] {
  const lines = rawText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return [];
  }

  const blocks: EditorialBlock[] = [];
  let paragraphLines: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (!paragraphLines.length) {
      return;
    }
    blocks.push({
      type: "paragraph",
      text: paragraphLines.join(" ").trim(),
    });
    paragraphLines = [];
  };

  const flushList = () => {
    if (!listItems.length) {
      return;
    }
    blocks.push({
      type: "list",
      items: listItems,
    });
    listItems = [];
  };

  for (const line of lines) {
    if (isListLine(line)) {
      flushParagraph();
      listItems.push(cleanListLine(line));
      continue;
    }
    flushList();
    paragraphLines.push(line);
  }

  flushParagraph();
  flushList();

  return blocks;
}

function parseEditorialText(
  content: string,
  defaults: {
    title: string;
    intro: string;
  }
): EditorialDocument {
  const normalized = normalizeText(content);
  if (!normalized) {
    return {
      title: defaults.title,
      intro: defaults.intro,
      sections: [],
      isEmpty: true,
    };
  }

  const rawChunks = normalized
    .split(/\n\s*\n+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);

  let title = defaults.title;
  let intro = defaults.intro;
  const sections: EditorialSection[] = [];
  let currentSection: EditorialSection | null = null;

  if (rawChunks[0]?.startsWith("#")) {
    title = cleanHeading(rawChunks.shift() || defaults.title) || defaults.title;
  }

  if (rawChunks.length && !looksLikeHeading(rawChunks[0].split("\n")[0]?.trim() || "")) {
    intro = rawChunks.shift() || defaults.intro;
  }

  for (const chunk of rawChunks) {
    const lines = chunk.split("\n").map((line) => line.trim()).filter(Boolean);
    const firstLine = lines[0] || "";
    const remainingText = lines.slice(1).join("\n").trim();
    const explicitHeading = isMarkdownHeading(firstLine);
    const inferredHeading =
      looksLikeHeading(firstLine) &&
      !(currentSection && currentSection.blocks.length === 0 && !explicitHeading);

    if (explicitHeading || inferredHeading) {
      currentSection = {
        title: cleanHeading(firstLine),
        blocks: createBlocks(remainingText),
      };
      sections.push(currentSection);
      continue;
    }

    if (!currentSection) {
      currentSection = {
        title: "Overview",
        blocks: [],
      };
      sections.push(currentSection);
    }

    currentSection.blocks.push(...createBlocks(chunk));
  }

  return {
    title,
    intro,
    sections,
    isEmpty: false,
  };
}

export async function loadEditorialDocument({
  relativeFilePath,
  relativeFilePaths,
  defaultTitle,
  defaultIntro,
}: LoadEditorialDocumentOptions): Promise<EditorialDocument> {
  const webAppRoot = resolveWebAppRoot();
  const candidatePaths = relativeFilePaths?.length
    ? relativeFilePaths
    : relativeFilePath
      ? [relativeFilePath]
      : [];

  let content = "";

  for (const candidatePath of candidatePaths) {
    const filePath = path.join(webAppRoot, candidatePath);
    const candidateContent = await readFile(filePath, "utf8").catch(() => "");
    if (normalizeText(candidateContent)) {
      content = candidateContent;
      break;
    }
  }

  return parseEditorialText(content, {
    title: defaultTitle,
    intro: defaultIntro,
  });
}
