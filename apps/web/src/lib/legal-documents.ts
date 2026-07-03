import "server-only";

import { promises as fs } from "fs";
import path from "path";

import {
  COMPANY_LEGAL_DOCUMENTS,
  CORPER_LEGAL_DOCUMENTS,
  LEGAL_DOCUMENTS,
  type LegalDocumentRecord,
  type LegalDocumentSlug,
} from "@/lib/legal-document-template";

const LEGAL_DOCUMENTS_DIRECTORY = path.join(process.cwd(), "src", "legal", "shared");
const LEGAL_ROOT_DIRECTORY = path.join(process.cwd(), "src", "legal");

function resolveLegalDocumentPath(slug: LegalDocumentSlug) {
  if (slug === "corper-subscription-terms-payment-policy") {
    return path.join(LEGAL_ROOT_DIRECTORY, `${slug}.md`);
  }

  return path.join(LEGAL_DOCUMENTS_DIRECTORY, `${slug}.md`);
}

async function loadDocuments(documents: readonly { slug: LegalDocumentSlug; title: string }[]) {
  return Promise.all(
    documents.map(async ({ slug, title }) => {
      const filePath = resolveLegalDocumentPath(slug);
      const content = await fs.readFile(filePath, "utf8");
      return {
        slug,
        title,
        content,
      } satisfies LegalDocumentRecord;
    })
  );
}

export async function getLegalDocuments() {
  return loadDocuments(LEGAL_DOCUMENTS);
}

export async function getCorperLegalDocuments() {
  return loadDocuments(CORPER_LEGAL_DOCUMENTS);
}

export async function getCompanyLegalDocuments() {
  return loadDocuments(COMPANY_LEGAL_DOCUMENTS);
}

export async function getLegalDocumentBySlug(slug: string) {
  const document = LEGAL_DOCUMENTS.find((entry) => entry.slug === slug);
  if (!document) {
    return null;
  }

  const filePath = resolveLegalDocumentPath(document.slug as LegalDocumentSlug);
  const content = await fs.readFile(filePath, "utf8");
  return {
    slug: document.slug as LegalDocumentSlug,
    title: document.title,
    content,
  } satisfies LegalDocumentRecord;
}
