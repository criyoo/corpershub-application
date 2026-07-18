export const SHARED_LEGAL_DOCUMENTS = [
  {
    slug: "acceptable-use-policy",
    title: "Acceptable Use Policy",
  },
  {
    slug: "background-verification-consent",
    title: "Background Verification and Consent Agreement",
  },
  {
    slug: "cookies-policy",
    title: "Cookies Policy",
  },
  {
    slug: "ppa-placement-disclaimer",
    title: "PPA Placement Disclaimer",
  },
  {
    slug: "privacy-policy",
    title: "Privacy Policy",
  },
  {
    slug: "terms-of-service",
    title: "Terms of Service",
  },
] as const;

export const CORPER_ONLY_LEGAL_DOCUMENTS = [
  {
    slug: "corper-subscription-terms-payment-policy",
    title: "Corper Subscription Terms & Payment Policy",
  },
] as const;

export const CORPER_LEGAL_DOCUMENTS = [
  ...SHARED_LEGAL_DOCUMENTS,
  ...CORPER_ONLY_LEGAL_DOCUMENTS,
] as const;

export const COMPANY_LEGAL_DOCUMENTS = SHARED_LEGAL_DOCUMENTS;
export const LEGAL_DOCUMENTS = CORPER_LEGAL_DOCUMENTS;

export type LegalDocumentSlug = (typeof LEGAL_DOCUMENTS)[number]["slug"];

export type LegalDocumentRecord = {
  slug: LegalDocumentSlug;
  title: string;
  content: string;
};

export type LegalDocumentTemplateValues = {
  name?: string | null;
  date?: string | null;
  nysc_callup_number?: string | null;
  nysc_state_code?: string | null;
  company_name?: string | null;
};

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function formatAgreementDate(value: Date | string = new Date()) {
  const resolvedDate = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat("en-NG", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(resolvedDate);
}

function applyLabeledLineValue(line: string, label: string, value: string) {
  if (!value) {
    return line;
  }

  const patterns = [
    new RegExp(`^(\\*\\*${escapeRegExp(label)}:\\*\\*\\s*)(?:_+|\\.{3,}|-+)?\\s*$`, "i"),
    new RegExp(`^(${escapeRegExp(label)}:)(?:\\s*)(?:_+|\\.{3,}|-+)?\\s*$`, "i"),
  ];

  for (const [index, pattern] of patterns.entries()) {
    if (pattern.test(line)) {
      return line.replace(pattern, index === 0 ? `$1${value}` : `$1 ${value}`);
    }
  }

  return line;
}

export function hydrateLegalDocumentContent(
  content: string,
  values: LegalDocumentTemplateValues
) {
  const signerName =
    values.name?.trim() || values.company_name?.trim() || "";
  const resolvedDate = values.date?.trim() || formatAgreementDate();
  const replacements: Record<string, string> = {
    "{{name}}": signerName,
    "{{date}}": resolvedDate,
    "{{nysc_callup_number}}": values.nysc_callup_number?.trim() || "",
    "{{nysc_state_code}}": values.nysc_state_code?.trim() || "",
    "{{company_name}}": values.company_name?.trim() || "",
  };

  let hydratedContent = content;
  for (const [token, replacement] of Object.entries(replacements)) {
    hydratedContent = hydratedContent.replaceAll(token, replacement);
  }

  hydratedContent = hydratedContent
    .split("\n")
    .map((line) => {
      let nextLine = line;
      nextLine = applyLabeledLineValue(nextLine, "Effective Date", resolvedDate);
      nextLine = applyLabeledLineValue(nextLine, "Last Updated", resolvedDate);
      nextLine = applyLabeledLineValue(nextLine, "Date", resolvedDate);
      nextLine = applyLabeledLineValue(nextLine, "Name", signerName);
      nextLine = applyLabeledLineValue(
        nextLine,
        "NYSC Call-up Number",
        values.nysc_callup_number?.trim() || ""
      );
      nextLine = applyLabeledLineValue(
        nextLine,
        "NYSC State Code",
        values.nysc_state_code?.trim() || ""
      );
      nextLine = applyLabeledLineValue(
        nextLine,
        "Company Name",
        values.company_name?.trim() || ""
      );
      return nextLine;
    })
    .join("\n");

  return hydratedContent;
}
