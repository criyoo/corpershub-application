import { promises as fs } from "node:fs";
import path from "node:path";

export type SupportFaqItem = {
  question: string;
  answer: string;
};

const FAQ_INTRO_LINES = new Set([
  "General FAQs",
  "(Visible to Everyone)",
  "Companies FAQs",
  "(Visible to Companies)",
  "Corpers FAQs",
  "(Visible to Corpers)",
]);

const FALLBACK_ROLE_FAQ: Record<"company" | "corper", SupportFaqItem[]> = {
  company: [
    {
      question: "How do company profiles become visible to corpers?",
      answer: "Complete your company profile so your listing can appear in privacy-safe search results and attract relevant corpers.",
    },
    {
      question: "Why can’t I see full corper identity immediately?",
      answer: "Corper discovery is privacy-safe by design. Detailed identity stays limited until the workflow progresses.",
    },
    {
      question: "How long does support take to respond?",
      answer: "Support chat targets a 1 hour response window. Email support targets a 24 hour response window.",
    },
    {
      question: "Can support help with company profile edits?",
      answer: "Yes. If a locked company field needs correction, send the exact issue through support so the team can review it.",
    },
  ],
  corper: [
    {
      question: "How do I unlock my full corper profile?",
      answer: "Submit and complete biodata, NIN, NYSC call-up, and NYSC state code verification. Once approved, the full profile flow opens.",
    },
    {
      question: "What if my verification submission fails?",
      answer: "The failed attempt appears in submission history with the actual error. Correct the value and submit again.",
    },
    {
      question: "How long does support take to respond?",
      answer: "Support chat targets a 1 hour response window. Email support targets a 24 hour response window.",
    },
    {
      question: "Can support change locked profile fields?",
      answer: "Yes. If a locked field needs admin intervention, contact support with the exact field and correction required.",
    },
  ],
};

function normalizeAnswer(lines: string[]) {
  const sections: string[] = [];
  let paragraph: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (paragraph.length) {
        sections.push(paragraph.join(" "));
        paragraph = [];
      }
      continue;
    }

    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      if (paragraph.length) {
        sections.push(paragraph.join(" "));
        paragraph = [];
      }
      sections.push(trimmed);
      continue;
    }

    paragraph.push(trimmed);
  }

  if (paragraph.length) {
    sections.push(paragraph.join(" "));
  }

  return sections.join("\n\n").trim();
}

function parseFaqMarkdown(content: string) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const items: SupportFaqItem[] = [];
  let currentQuestion: string | null = null;
  let currentAnswerLines: string[] = [];

  const flushCurrent = () => {
    if (!currentQuestion) {
      return;
    }

    const answer = normalizeAnswer(currentAnswerLines);
    if (answer) {
      items.push({
        question: currentQuestion,
        answer,
      });
    }

    currentQuestion = null;
    currentAnswerLines = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      currentAnswerLines.push("");
      continue;
    }

    if (FAQ_INTRO_LINES.has(line)) {
      continue;
    }

    if (line.endsWith("?")) {
      flushCurrent();
      currentQuestion = line;
      continue;
    }

    if (currentQuestion) {
      currentAnswerLines.push(line);
    }
  }

  flushCurrent();
  return items;
}

async function readFaqFile(filename: string) {
  const filePath = path.join(process.cwd(), "src", "components", "support", filename);
  return fs.readFile(filePath, "utf8");
}

async function readFirstFaqFile(fileNames: string[]) {
  for (const fileName of fileNames) {
    try {
      return await readFaqFile(fileName);
    } catch {
      continue;
    }
  }

  return "";
}

export async function loadSupportFaqItems(role: "company" | "corper") {
  const [generalContent, roleContent] = await Promise.all([
    readFirstFaqFile(["general_faq.md"]),
    role === "company"
      ? readFirstFaqFile(["companies_faq.md", "comapnies_faq.md"])
      : readFirstFaqFile(["corpers_faq.md", "corpers_faq.mq"]),
  ]);

  const roleItems = parseFaqMarkdown(roleContent);

  return [
    ...parseFaqMarkdown(generalContent),
    ...(roleItems.length ? roleItems : FALLBACK_ROLE_FAQ[role]),
  ];
}
