"use client";

import clsx from "clsx";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileText,
  Fingerprint,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { PpaDisclaimerNote } from "@/components/legal/ppa-disclaimer-note";
import { useAuth } from "@/components/providers/auth-provider";
import {
  useCorperVerificationDraft,
  type CorperVerificationDraft,
} from "@/components/providers/corper-verification-draft-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { WORLD_COUNTRIES } from "@/lib/countries";
import { resolveMediaUrl } from "@/lib/media";
import { setSession } from "@/lib/session";
import {
  normalizeMobileNumber,
  normalizeNigerianMobileInput,
  normalizeNyscCallupNumber,
  normalizeNyscStateCode,
  validateNinNumber,
  validateNigerianMobileNumber,
  validateNyscCallupNumber,
  validateNyscStateCode,
  validateUniversityMatriculationNumber,
} from "@/lib/nigerian-validation";
import { CORPER_GENDERS, NIGERIAN_STATES } from "@/lib/nigerian-reference-data";
import { formatVerificationStatus, formatVerificationType } from "@/lib/verification";

type Attempt = {
  id: string;
  verification_type: string;
  status: string;
  submitted_value_masked: string;
  created_at: string;
  review_note?: string;
};

type AttemptResponse = {
  results: Attempt[];
};

type CorperProfile = {
  verification_status: string;
  biodata_verification_status: string;
  nin_verification_status: string;
  nysc_callup_verification_status: string;
  nysc_state_code_verification_status: string;
  full_name: string;
  first_name: string;
  middle_name: string;
  surname: string;
  date_of_birth: string | null;
  gender: string;
  mobile_number: string;
  state_of_origin: string;
  country_of_birth: string;
  university_matriculation_number: string;
  masked_nin_number: string;
  masked_callup_number: string;
  nysc_callup_document: string | null;
  masked_state_code: string;
  nysc_state_code_document: string | null;
  is_complete: boolean;
  terms_accepted: boolean;
};

type DocumentVerificationType = "biodata" | "nin" | "callup" | "state_code";
type UploadableDocumentVerificationType = "callup" | "state_code";
type VerificationDraftFieldKey =
  | "first_name"
  | "middle_name"
  | "surname"
  | "date_of_birth"
  | "gender"
  | "mobile_number"
  | "state_of_origin"
  | "country_of_birth"
  | "university_matriculation_number"
  | "nin"
  | "callup"
  | "callup_document"
  | "state_code"
  | "state_code_document";
type NormalizedVerificationDraftResult =
  | { error: string; fields?: VerificationDraftFieldKey[] }
  | { draft: CorperVerificationDraft };
const VERIFICATION_DRAFT_STORAGE_KEY = "corpershub.corper-verification-draft";
const TEMPORARY_MISSING_FIELD_CLASS_NAME =
  "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50";

const REQUIRED_VERIFICATION_DRAFT_FIELDS: Array<{
  key: VerificationDraftFieldKey;
  label: string;
  isMissing: (draft: CorperVerificationDraft) => boolean;
}> = [
    {
      key: "first_name",
      label: "First name",
      isMissing: (draft) => !draft.biodata.first_name.trim(),
    },
    {
      key: "middle_name",
      label: "Middle name",
      isMissing: (draft) => !draft.biodata.middle_name.trim(),
    },
    {
      key: "surname",
      label: "Surname",
      isMissing: (draft) => !draft.biodata.surname.trim(),
    },
    {
      key: "date_of_birth",
      label: "Date of birth",
      isMissing: (draft) => !draft.biodata.date_of_birth,
    },
    {
      key: "state_of_origin",
      label: "State of origin",
      isMissing: (draft) => !draft.biodata.state_of_origin.trim(),
    },
    {
      key: "country_of_birth",
      label: "Country of birth",
      isMissing: (draft) => !draft.biodata.country_of_birth.trim(),
    },
    {
      key: "gender",
      label: "Gender",
      isMissing: (draft) => !draft.biodata.gender.trim(),
    },
    {
      key: "mobile_number",
      label: "Mobile number",
      isMissing: (draft) => !draft.biodata.mobile_number.trim(),
    },
    {
      key: "university_matriculation_number",
      label: "University matriculation number",
      isMissing: (draft) => !draft.biodata.university_matriculation_number.trim(),
    },
    {
      key: "nin",
      label: "NIN",
      isMissing: (draft) => !draft.nin.submitted_value.trim(),
    },
    {
      key: "callup",
      label: "NYSC call-up number",
      isMissing: (draft) => !draft.callup.submitted_value.trim(),
    },
    {
      key: "callup_document",
      label: "NYSC call-up document",
      isMissing: (draft) =>
        (!(draft.callup.document instanceof File) || draft.callup.document.size === 0) &&
        !draft.callup.document_name.trim(),
    },
    {
      key: "state_code",
      label: "NYSC state code",
      isMissing: (draft) => !draft.state_code.submitted_value.trim(),
    },
    {
      key: "state_code_document",
      label: "NYSC state code document",
      isMissing: (draft) =>
        (!(draft.state_code.document instanceof File) || draft.state_code.document.size === 0) &&
        !draft.state_code.document_name.trim(),
    },
  ];

const verificationDocuments = [
  {
    type: "biodata" as const,
    label: "Biodata",
    title: "Fullname, DoB, & Matric Number",
    icon: FileText,
  },
  {
    type: "nin" as const,
    label: "NIN",
    title: "National Identification Number",
    placeholder: "Enter your 11-digit NIN",
    maxLength: 11,
    icon: Fingerprint,
  },
  {
    type: "callup" as const,
    label: "NYSC call-up",
    title: "NYSC Call-up Number",
    placeholder: "e.g NYSC/LAG/2025/54321",
    maxLength: 20,
    icon: FileText,
  },
  {
    type: "state_code" as const,
    label: "NYSC state code",
    title: "NYSC State Code",
    placeholder: "e.g NYSC/LG/26B/72673",
    maxLength: 18,
    icon: ShieldCheck,
  },
];

function VerificationField({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={clsx("grid min-w-0 gap-1.5", className)}>
      <p className="px-1 text-[7px] font-medium uppercase tracking-[0.18em] text-lime">{label}</p>
      {children}
    </div>
  );
}

function canSubmitDocument(status: string) {
  return status !== "verified";
}

function normalizeStatus(status: string) {
  switch (status.toLowerCase()) {
    case "approved":
      return "verified";
    case "under_review":
      return "pending";
    default:
      return status.toLowerCase();
  }
}

function getStatusMeta(status: string, reviewNote?: string) {
  switch (normalizeStatus(status)) {
    case "verified":
      return {
        label: "Verified",
        description: "Approved.",
        badgeClass: "border-lime/35 bg-lime/12 text-lime",
        panelClass:
          "border-lime/20 bg-[linear-gradient(145deg,rgba(124,217,161,0.12),rgba(4,21,15,0.06)),linear-gradient(180deg,rgba(9,27,19,0.9),rgba(8,19,14,0.92))]",
        iconClass: "border-lime/20 bg-lime/12 text-lime",
        Icon: CheckCircle2,
      };
    case "pending":
      return {
        label: "Pending review",
        description: "Submitted successfully and waiting for admin review.",
        badgeClass: "border-[#F4D35E]/35 bg-[#F4D35E]/10 text-[#F7E29A]",
        panelClass:
          "border-[#F4D35E]/18 bg-[linear-gradient(145deg,rgba(244,211,94,0.12),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(17,24,15,0.94),rgba(8,19,14,0.94))]",
        iconClass: "border-[#F4D35E]/20 bg-[#F4D35E]/10 text-[#F7E29A]",
        Icon: Clock3,
      };
    case "rejected":
      return {
        label: "Failed",
        description: "Verification failed. Correct the value and submit it again.",
        badgeClass: "border-coral/35 bg-coral/10 text-[#F3A3A3]",
        panelClass:
          "border-coral/20 bg-[linear-gradient(145deg,rgba(217,95,95,0.14),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(28,13,13,0.94),rgba(8,19,14,0.94))]",
        iconClass: "border-coral/20 bg-coral/12 text-[#F3A3A3]",
        Icon: CircleAlert,
      };
    case "failed":
      return {
        label: "Failed",
        description: reviewNote || "Submission failed before it could be sent for admin review.",
        badgeClass: "border-coral/35 bg-coral/10 text-[#F3A3A3]",
        panelClass:
          "border-coral/20 bg-[linear-gradient(145deg,rgba(217,95,95,0.14),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(28,13,13,0.94),rgba(8,19,14,0.94))]",
        iconClass: "border-coral/20 bg-coral/12 text-[#F3A3A3]",
        Icon: CircleAlert,
      };
    default:
      return {
        label: "Not submitted",
        description: "Submit this document to start the verification process.",
        badgeClass: "border-white/14 bg-white/[0.05] text-white/78",
        panelClass:
          "border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(11,38,27,0.9),rgba(7,20,14,0.94))]",
        iconClass: "border-white/12 bg-white/[0.05] text-white/80",
        Icon: Sparkles,
      };
  }
}

function getDocumentStatus(profile: CorperProfile | null, verificationType: DocumentVerificationType) {
  return verificationType === "biodata"
    ? profile?.biodata_verification_status ?? "unsubmitted"
    : verificationType === "nin"
      ? profile?.nin_verification_status ?? "unsubmitted"
      : verificationType === "callup"
        ? profile?.nysc_callup_verification_status ?? "unsubmitted"
        : profile?.nysc_state_code_verification_status ?? "unsubmitted";
}

function isDocumentVerificationType(value: string): value is DocumentVerificationType {
  return value === "biodata" || value === "nin" || value === "callup" || value === "state_code";
}

function getAttemptDisplayStatus(profile: CorperProfile | null, attempt: Attempt) {
  if (!isDocumentVerificationType(attempt.verification_type) || normalizeStatus(attempt.status) !== "pending") {
    return attempt.status;
  }

  const documentStatus = getDocumentStatus(profile, attempt.verification_type);
  return normalizeStatus(documentStatus) === "verified" ? documentStatus : attempt.status;
}

function getStoredMaskedValue(profile: CorperProfile | null, verificationType: DocumentVerificationType) {
  if (verificationType === "biodata") {
    if (!profile?.full_name || !profile?.date_of_birth) {
      return "";
    }
    return [
      profile.full_name,
      profile.date_of_birth,
      profile.university_matriculation_number,
    ]
      .filter(Boolean)
      .join(" | ");
  }
  if (verificationType === "nin") {
    return profile?.masked_nin_number ?? "";
  }
  if (verificationType === "callup") {
    return profile?.masked_callup_number ?? "";
  }
  return profile?.masked_state_code ?? "";
}

function supportsDocumentUpload(
  verificationType: DocumentVerificationType
): verificationType is UploadableDocumentVerificationType {
  return verificationType === "callup" || verificationType === "state_code";
}

function getUploadedDocument(profile: CorperProfile | null, verificationType: DocumentVerificationType) {
  if (verificationType === "callup") {
    return profile?.nysc_callup_document ?? null;
  }
  if (verificationType === "state_code") {
    return profile?.nysc_state_code_document ?? null;
  }
  return null;
}

function getDocumentFileName(path?: string | null) {
  if (!path) {
    return "";
  }
  const normalizedPath = path.split("?")[0] ?? path;
  return normalizedPath.split("/").filter(Boolean).pop() ?? "";
}

function formatDateTime(value: string) {
  const parts = new Intl.DateTimeFormat("en-NG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date(value));
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${values.day} ${values.month?.toUpperCase() ?? ""} ${values.year} ${values.hour}:${values.minute}:${values.second}`;
}

function getSubmissionButtonState(status: string, isSubmitting: boolean) {
  if (isSubmitting) {
    return {
      label: "Submitting...",
      disabled: true,
      className: "",
    };
  }

  switch (normalizeStatus(status)) {
    case "pending":
      return {
        label: "Submitted",
        disabled: true,
        className:
          "bg-[linear-gradient(135deg,#8A5A2B_0%,#6E441F_100%)] text-white shadow-[0_18px_35px_rgba(110,68,31,0.28)] hover:brightness-100 disabled:opacity-100",
      };
    case "verified":
      return {
        label: "Verified",
        disabled: true,
        className:
          "bg-[#6B7280] text-white shadow-none hover:bg-[#6B7280] disabled:opacity-100",
      };
    case "rejected":
      return {
        label: "Resubmit for review",
        disabled: false,
        className: "",
      };
    default:
      return {
        label: "Submit for review",
        disabled: false,
        className: "",
      };
  }
}

function formatVerificationDocumentLabels(documents: typeof verificationDocuments) {
  if (documents.length === 0) {
    return "";
  }
  if (documents.length === 1) {
    return documents[0].label;
  }
  if (documents.length === 2) {
    return `${documents[0].label} and ${documents[1].label}`;
  }

  return `${documents.slice(0, -1).map((document) => document.label).join(", ")}, and ${documents[documents.length - 1].label
    }`;
}

function getHeroCopy(profile: CorperProfile | null) {
  const verifiedDocuments = verificationDocuments.filter(
    (document) => normalizeStatus(getDocumentStatus(profile, document.type)) === "verified"
  );
  const submittedDocuments = verificationDocuments.filter(
    (document) => normalizeStatus(getDocumentStatus(profile, document.type)) !== "unsubmitted"
  );
  const documentsNeedingVerification = verificationDocuments.filter(
    (document) => normalizeStatus(getDocumentStatus(profile, document.type)) !== "verified"
  );

  if (verifiedDocuments.length === verificationDocuments.length) {
    return {
      title: "All records are verified",
      description: "Your biodata, NIN, NYSC call-up number, and NYSC state code are approved.",
    };
  }

  if (submittedDocuments.length === 0) {
    return {
      title: "Corper identity verification",
      description: "Submit all verification data and wait for approval.",
    };
  }

  const remainingCount = documentsNeedingVerification.length;
  const remainingLabel = remainingCount === 1 ? "record needs" : "records need";

  return {
    title: `${verifiedDocuments.length} of ${verificationDocuments.length} records are verified`,
    description: `${remainingCount} ${remainingLabel} verification: ${formatVerificationDocumentLabels(
      documentsNeedingVerification
    )}.`,
  };
}

function getNextStep(documentsVerified: boolean, isComplete: boolean | undefined) {
  if (!documentsVerified) {
    return "Submit all documents";
  }

  if (!isComplete) {
    return "Complete your profile";
  }

  return "Profile ready";
}

function buildDraftFullName(draft: CorperVerificationDraft["biodata"]) {
  return [draft.first_name, draft.middle_name, draft.surname]
    .map((part) => part.trim())
    .filter(Boolean)
    .join(" ");
}

function getMissingVerificationDraftFields(draft: CorperVerificationDraft) {
  return REQUIRED_VERIFICATION_DRAFT_FIELDS.filter((field) => field.isMissing(draft));
}

function persistVerificationDraftForTerms(draft: CorperVerificationDraft, ownerEmail: string | null) {
  if (typeof window === "undefined" || !ownerEmail) {
    return;
  }

  window.sessionStorage.setItem(
    VERIFICATION_DRAFT_STORAGE_KEY,
    JSON.stringify({
      owner_email: ownerEmail,
      draft: {
        biodata: draft.biodata,
        nin: draft.nin,
        callup: {
          submitted_value: draft.callup.submitted_value,
          document_name: draft.callup.document?.name ?? draft.callup.document_name,
        },
        state_code: {
          submitted_value: draft.state_code.submitted_value,
          document_name: draft.state_code.document?.name ?? draft.state_code.document_name,
        },
      },
    })
  );
}

function persistTermsNavigationSession(session: ReturnType<typeof useAuth>["session"]) {
  if (!session) {
    return;
  }

  setSession({
    ...session,
    user: {
      ...session.user,
      profile_path: "/corper/profile/terms",
      profile_completed: false,
    },
  });
}

function normalizeVerificationDraftForLegalStep(
  draft: CorperVerificationDraft
): NormalizedVerificationDraftResult {
  const fullName = buildDraftFullName(draft.biodata);
  if (!draft.biodata.first_name.trim()) {
    return { error: "Complete all verification field before continue: First name is required.", fields: ["first_name"] } as const;
  }
  if (!draft.biodata.middle_name.trim()) {
    return { error: "Complete all verification field before continue: Middle name is required.", fields: ["middle_name"] } as const;
  }
  if (!draft.biodata.surname.trim()) {
    return { error: "Complete all verification field before continue: Surname is required.", fields: ["surname"] } as const;
  }
  if (!draft.biodata.date_of_birth) {
    return { error: "Complete all verification field before continue: Date of birth is required.", fields: ["date_of_birth"] } as const;
  }
  if (!draft.biodata.gender.trim()) {
    return { error: "Complete all verification field before continue: Gender is required.", fields: ["gender"] } as const;
  }
  if (!draft.biodata.state_of_origin.trim()) {
    return { error: "Complete all verification field before continue: State of origin is required.", fields: ["state_of_origin"] } as const;
  }
  if (!draft.biodata.country_of_birth.trim()) {
    return { error: "Complete all verification field before continue: Country of birth is required.", fields: ["country_of_birth"] } as const;
  }

  const mobileValidation = validateNigerianMobileNumber(
    draft.biodata.mobile_number,
    "Mobile number",
    true,
    false
  );
  if (mobileValidation.error) {
    return { error: mobileValidation.error, fields: ["mobile_number"] } as const;
  }

  const matriculationValidation = validateUniversityMatriculationNumber(
    draft.biodata.university_matriculation_number
  );
  if (
    draft.biodata.university_matriculation_number.trim() &&
    matriculationValidation.error
  ) {
    return { error: matriculationValidation.error, fields: ["university_matriculation_number"] } as const;
  }

  const ninValidation = validateNinNumber(draft.nin.submitted_value);
  if (ninValidation.error) {
    return { error: ninValidation.error, fields: ["nin"] } as const;
  }

  const callupValidation = validateNyscCallupNumber(draft.callup.submitted_value);
  if (callupValidation.error) {
    return { error: callupValidation.error, fields: ["callup"] } as const;
  }
  if (
    (!(draft.callup.document instanceof File) || draft.callup.document.size === 0) &&
    !draft.callup.document_name.trim()
  ) {
    return { error: "Upload your NYSC call-up document before continuing.", fields: ["callup_document"] } as const;
  }

  const stateCodeValidation = validateNyscStateCode(draft.state_code.submitted_value);
  if (stateCodeValidation.error) {
    return { error: stateCodeValidation.error, fields: ["state_code"] } as const;
  }
  if (
    (!(draft.state_code.document instanceof File) || draft.state_code.document.size === 0) &&
    !draft.state_code.document_name.trim()
  ) {
    return { error: "Upload your NYSC state code document before continuing.", fields: ["state_code_document"] } as const;
  }

  return {
    draft: {
      biodata: {
        first_name: draft.biodata.first_name.trim(),
        middle_name: draft.biodata.middle_name.trim(),
        surname: draft.biodata.surname.trim(),
        date_of_birth: draft.biodata.date_of_birth,
        gender: draft.biodata.gender.trim(),
        mobile_number: mobileValidation.normalizedValue,
        state_of_origin: draft.biodata.state_of_origin.trim(),
        country_of_birth: draft.biodata.country_of_birth.trim(),
        university_matriculation_number:
          draft.biodata.university_matriculation_number.trim()
            ? matriculationValidation.normalizedValue
            : "",
      },
      nin: {
        submitted_value: ninValidation.normalizedValue,
      },
      callup: {
        submitted_value: callupValidation.normalizedValue,
        document: draft.callup.document,
        document_name: draft.callup.document?.name ?? draft.callup.document_name,
      },
      state_code: {
        submitted_value: stateCodeValidation.normalizedValue,
        document: draft.state_code.document,
        document_name: draft.state_code.document?.name ?? draft.state_code.document_name,
      },
    },
  } as const;
}

function VerificationOverviewSkeleton() {
  return (
    <Card className="grid gap-5 p-6 animate-[chat-panel-in_450ms_ease-out]">
      <div className="grid gap-3">
        <Skeleton className="h-12 w-full max-w-[24rem]" />
        <Skeleton className="h-5 w-full max-w-[34rem]" />
        <Skeleton className="h-5 w-full max-w-[30rem]" />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-28 w-full rounded-[24px]" />
        <Skeleton className="h-28 w-full rounded-[24px]" />
        <Skeleton className="h-28 w-full rounded-[24px]" />
      </div>
    </Card>
  );
}

function VerificationCardSkeleton() {
  return (
    <Card className="grid gap-5 p-6 animate-[chat-bubble-in_500ms_ease-out]">
      <div className="flex items-start justify-between gap-4">
        <Skeleton className="h-14 w-14 rounded-[20px]" />
        <Skeleton className="h-8 w-32 rounded-full" />
      </div>
      <div className="grid gap-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-full max-w-[18rem]" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-4/5" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-28 w-full rounded-[24px]" />
        <Skeleton className="h-28 w-full rounded-[24px]" />
      </div>
      <Skeleton className="h-40 w-full rounded-[24px]" />
    </Card>
  );
}

export default function CorperVerificationPage() {
  const router = useRouter();
  const { hydrated, session, updateSession } = useAuth();
  const {
    draft: verificationDraft,
    hydrated: verificationDraftHydrated,
    replaceDraft,
    clearDraft,
  } = useCorperVerificationDraft();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "corper";
  const attempts = useApiQuery<AttemptResponse>("/verification/attempts/", protectedQueryEnabled, 10000);
  const profile = useApiQuery<CorperProfile>("/corpers/me/", protectedQueryEnabled, 10000);
  const [submittingType, setSubmittingType] = useState<DocumentVerificationType | null>(null);
  const [selectedDocuments, setSelectedDocuments] = useState<
    Record<UploadableDocumentVerificationType, File | null>
  >({
    callup: null,
    state_code: null,
  });
  const [documentInputVersion, setDocumentInputVersion] = useState<
    Record<UploadableDocumentVerificationType, number>
  >({
    callup: 0,
    state_code: 0,
  });
  const [draftDateOfBirthInputType, setDraftDateOfBirthInputType] = useState<"text" | "date">(
    verificationDraft.biodata.date_of_birth ? "date" : "text"
  );
  const [profileDateOfBirthInputType, setProfileDateOfBirthInputType] = useState<"text" | "date">(
    "text"
  );
  const [profileGenderValue, setProfileGenderValue] = useState("");
  const [profileStateOfOriginValue, setProfileStateOfOriginValue] = useState("");
  const [highlightedDraftFields, setHighlightedDraftFields] = useState<Set<VerificationDraftFieldKey>>(
    () => new Set()
  );

  const sortedAttempts = [...(attempts.data?.results ?? [])].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  );
  const latestAttemptByType: Record<DocumentVerificationType, Attempt | null> = {
    biodata: sortedAttempts.find((attempt) => attempt.verification_type === "biodata") ?? null,
    nin: sortedAttempts.find((attempt) => attempt.verification_type === "nin") ?? null,
    callup: sortedAttempts.find((attempt) => attempt.verification_type === "callup") ?? null,
    state_code: sortedAttempts.find((attempt) => attempt.verification_type === "state_code") ?? null,
  };
  const completedDocumentsCount = verificationDocuments.filter(
    (document) => normalizeStatus(getDocumentStatus(profile.data, document.type)) === "verified"
  ).length;
  const documentsVerified = completedDocumentsCount === verificationDocuments.length;
  const progressPercent = Math.round((completedDocumentsCount / verificationDocuments.length) * 100);
  const isInitialProfileLoad = profile.loading && !profile.data;
  const isInitialAttemptsLoad = attempts.loading && !attempts.data;
  const heroCopy = getHeroCopy(profile.data ?? null);
  const nextStep = getNextStep(documentsVerified, profile.data?.is_complete);
  const loadErrors = [profile.error, attempts.error].filter(Boolean);
  const verificationRedirectPath = profile.data?.is_complete
    ? "/corper/profile?edit=1"
    : "/corper/profile";

  useEffect(() => {
    if (profile.data?.terms_accepted) {
      clearDraft();
    }
  }, [clearDraft, profile.data?.terms_accepted]);

  useEffect(() => {
    setDraftDateOfBirthInputType(verificationDraft.biodata.date_of_birth ? "date" : "text");
  }, [verificationDraft.biodata.date_of_birth]);

  useEffect(() => {
    setProfileDateOfBirthInputType(profile.data?.date_of_birth ? "date" : "text");
  }, [profile.data?.date_of_birth]);

  useEffect(() => {
    setProfileGenderValue(profile.data?.gender ?? "");
    setProfileStateOfOriginValue(profile.data?.state_of_origin ?? "");
  }, [profile.data?.gender, profile.data?.state_of_origin]);

  useEffect(() => {
    if (highlightedDraftFields.size === 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setHighlightedDraftFields(new Set());
    }, 3500);

    return () => window.clearTimeout(timeoutId);
  }, [highlightedDraftFields]);

  useEffect(() => {
    if (!session || session.user.role !== "corper" || typeof profile.data?.is_complete !== "boolean") {
      return;
    }

    const nextProfilePath = documentsVerified
      ? profile.data.terms_accepted
        ? "/corper/profile"
        : "/corper/profile/terms"
      : "/corper/verification";
    const nextProfileCompleted = documentsVerified && profile.data.is_complete;

    if (
      session.user.profile_path !== nextProfilePath ||
      session.user.profile_completed !== nextProfileCompleted
    ) {
      updateSession({
        ...session,
        user: {
          ...session.user,
          profile_path: nextProfilePath,
          profile_completed: nextProfileCompleted,
        },
      });
    }
  }, [documentsVerified, profile.data?.is_complete, profile.data?.terms_accepted, session, updateSession]);

  function isDraftFieldHighlighted(field: VerificationDraftFieldKey) {
    return highlightedDraftFields.has(field);
  }

  function getDraftFieldClassName(field: VerificationDraftFieldKey, className: string) {
    return clsx(className, isDraftFieldHighlighted(field) && TEMPORARY_MISSING_FIELD_CLASS_NAME);
  }

  function clearDraftFieldHighlight(field: VerificationDraftFieldKey) {
    setHighlightedDraftFields((current) => {
      if (!current.has(field)) {
        return current;
      }
      const nextFields = new Set(current);
      nextFields.delete(field);
      return nextFields;
    });
  }

  function handleProceedToLegalDocuments() {
    const missingFields = getMissingVerificationDraftFields(verificationDraft);
    if (missingFields.length) {
      setHighlightedDraftFields(new Set(missingFields.map((field) => field.key)));
      toast.error(`Complete required verification fields: ${missingFields.map((field) => field.label).join(", ")}.`);
      return;
    }

    const normalizedDraft = normalizeVerificationDraftForLegalStep(verificationDraft);
    if ("error" in normalizedDraft) {
      setHighlightedDraftFields(new Set(normalizedDraft.fields ?? []));
      toast.error(normalizedDraft.error);
      return;
    }

    setHighlightedDraftFields(new Set());
    replaceDraft(normalizedDraft.draft);
    persistVerificationDraftForTerms(normalizedDraft.draft, session?.user.email ?? null);
    persistTermsNavigationSession(session);
    router.push("/corper/profile/terms");
  }

  async function submitVerification(
    verificationType: DocumentVerificationType,
    payload: FormData | Record<string, string>
  ) {
    const requestBody =
      payload instanceof FormData
        ? payload
        : JSON.stringify({ verification_type: verificationType, ...payload });
    await apiFetch("/verification/attempts/", {
      method: "POST",
      formData: payload instanceof FormData,
      body: requestBody,
    });
  }

  async function handleBiodataSubmit(formData: FormData) {
    const firstName = String(formData.get("first_name") ?? "").trim();
    const middleName = String(formData.get("middle_name") ?? "").trim();
    const surname = String(formData.get("surname") ?? "").trim();
    const dateOfBirth = String(formData.get("date_of_birth") ?? "").trim();
    const gender = String(formData.get("gender") ?? "").trim();
    const mobileNumber = String(formData.get("mobile_number") ?? "").trim();
    const stateOfOrigin = String(formData.get("state_of_origin") ?? "").trim();
    const countryOfBirth = String(formData.get("country_of_birth") ?? "").trim();
    const universityMatriculationNumber = String(
      formData.get("university_matriculation_number") ?? ""
    ).trim();

    if (!firstName || !surname || !dateOfBirth || !gender || !mobileNumber) {
      toast.error("Enter your first name, surname, date of birth, gender, and mobile number.");
      return;
    }

    const mobileValidation = validateNigerianMobileNumber(
      mobileNumber,
      "Mobile number",
      true,
      false
    );
    if (mobileValidation.error) {
      toast.error(mobileValidation.error);
      return;
    }

    const matriculationValidation = universityMatriculationNumber
      ? validateUniversityMatriculationNumber(universityMatriculationNumber)
      : { error: null, normalizedValue: "" };
    if (matriculationValidation.error) {
      toast.error(matriculationValidation.error);
      return;
    }

    setSubmittingType("biodata");

    try {
      await submitVerification("biodata", {
        first_name: firstName,
        middle_name: middleName,
        surname,
        date_of_birth: dateOfBirth,
        gender,
        mobile_number: mobileValidation.normalizedValue,
        state_of_origin: stateOfOrigin,
        country_of_birth: countryOfBirth,
        university_matriculation_number: matriculationValidation.normalizedValue,
      });
      toast.success("Verification request submitted.");
      await Promise.all([attempts.refetch(), profile.refetch()]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to submit verification.");
    } finally {
      setSubmittingType(null);
    }
  }

  async function handleDocumentSubmit(verificationType: DocumentVerificationType, formData: FormData) {
    const rawSubmittedValue = String(formData.get("submitted_value") ?? "").trim();

    if (!rawSubmittedValue) {
      toast.error("Enter the document value before submitting.");
      return;
    }

    const validationResult =
      verificationType === "nin"
        ? validateNinNumber(rawSubmittedValue)
        : verificationType === "callup"
          ? validateNyscCallupNumber(rawSubmittedValue)
          : validateNyscStateCode(rawSubmittedValue);

    if (validationResult.error) {
      toast.error(validationResult.error);
      return;
    }

    if (supportsDocumentUpload(verificationType)) {
      const document = formData.get("document");
      if (!(document instanceof File) || document.size === 0) {
        toast.error("Upload the NYSC document before submitting.");
        return;
      }
    }

    setSubmittingType(verificationType);

    try {
      if (supportsDocumentUpload(verificationType)) {
        const payload = new FormData();
        payload.set("verification_type", verificationType);
        payload.set("submitted_value", validationResult.normalizedValue);
        const document = formData.get("document");
        if (document instanceof File && document.size > 0) {
          payload.set("document", document);
        }
        await submitVerification(verificationType, payload);
      } else {
        await submitVerification(verificationType, {
          submitted_value: validationResult.normalizedValue,
        });
      }
      toast.success("Verification request submitted.");
      if (supportsDocumentUpload(verificationType)) {
        setSelectedDocuments((current) => ({ ...current, [verificationType]: null }));
        setDocumentInputVersion((current) => ({
          ...current,
          [verificationType]: current[verificationType] + 1,
        }));
      }
      await Promise.all([attempts.refetch(), profile.refetch()]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to submit verification.");
    } finally {
      setSubmittingType(null);
    }
  }

  const titleBadge = isInitialProfileLoad ? (
    <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white">
      <Clock3 className="h-5 w-5 text-white/70" />
      Loading status
    </div>
  ) : (
    <div
      className={clsx(
        "inline-flex items-center gap-3 rounded-full px-4 py-2 text-[12px] font-semibold justify-end uppercase tracking-[0.18em]",
        documentsVerified
          ? "border border-lime/35 bg-lime/12"
          : "border border-white/10 bg-white/[0.05]"
      )}
    >
      {documentsVerified ? (
        <ShieldCheck className="h-5 w-5 text-[#75f612]" />
      ) : (
        <Sparkles className="h-5 w-5 text-[#F7E29A]" />
      )}
      {completedDocumentsCount}/{verificationDocuments.length} documents verified
    </div>
  );

  return (
    <DashboardShell
      role="corper"
      title="Verification Center"
      titleBadge={titleBadge}
      hideDefaultHeaderAside
      hideCorperBanner
    >
      <div className="grid gap-5">
        {loadErrors.length ? (
          <Card className="border-coral/25 bg-coral/10 animate-[chat-panel-in_350ms_ease-out]">
            <p className="text-xs uppercase tracking-[0.22em] text-[#F3A3A3]">Status issue</p>
            <h2 className="mt-3 font-display text-2xl text-white">We could not refresh every verification detail</h2>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-mist">
              {loadErrors.join(" ")}
            </p>
          </Card>
        ) : null}

        {!isInitialProfileLoad ? (
          <Card className="grid gap-4 border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(11,38,27,0.92),rgba(7,20,14,0.96))] p-5 animate-[chat-panel-in_500ms_ease-out]">
            <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/55">
              <span>Verification progress</span>
              <span>{progressPercent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,#7CD9A1_0%,#F4D35E_100%)] transition-[width] duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="flex flex-wrap gap-3">
              {profile.data?.terms_accepted ? (
                <Link
                  href={verificationRedirectPath}
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-ink transition duration-200 hover:bg-lime hover:text-[#E6D28C]"
                >
                  {profile.data?.is_complete ? "Open profile" : "Complete profile"}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              ) : (
                <Button
                  type="button"
                  variant="secondary"
                  className="gap-2"
                  onClick={handleProceedToLegalDocuments}
                  disabled={!verificationDraftHydrated}
                >
                  Review terms & conditions
                  <ArrowRight className="h-4 w-4" />
                </Button>
              )}
              <Link
                href="#verification-activity"
                className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.05] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                View activity
              </Link>
            </div>
          </Card>
        ) : null}

        {isInitialProfileLoad ? (
          <VerificationOverviewSkeleton />
        ) : !profile.data?.terms_accepted ? (
          verificationDraftHydrated ? (
            <Card className="grid gap-6 border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.12),rgba(4,21,15,0.08)),linear-gradient(180deg,#163F2D_0%,#0A2117_100%)] p-6">
              <div className="grid gap-2">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Verification first</p>
                <h2 className="font-display text-2xl text-white">
                  Complete verification
                </h2>
                <p className="text-sm leading-7 text-lime/70">
                  Verification will remain pending until legal terms and agreement are accepted.
                </p>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <Card className="grid gap-4 border-white/10 bg-black/10 p-5">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.10em] text-lime">Biodata</p>
                    <h3 className="mt-2 font-display text-[16px] text-white">
                      Biodata Information
                    </h3>
                  </div>
                  <div className="grid gap-3">
                    <div className="grid gap-3 md:grid-cols-3">
                      <VerificationField label="First name">
                        <Input
                          value={verificationDraft.biodata.first_name}
                          onChange={(event) => {
                            clearDraftFieldHighlight("first_name");
                            replaceDraft({
                              ...verificationDraft,
                              biodata: {
                                ...verificationDraft.biodata,
                                first_name: event.target.value,
                              },
                            });
                          }}
                          placeholder="First name"
                          autoCapitalize="words"
                          className={getDraftFieldClassName("first_name", "h-12 bg-white/[0.05] text-xs")}
                        />
                      </VerificationField>
                      <VerificationField label="Middle name">
                        <Input
                          value={verificationDraft.biodata.middle_name}
                          onChange={(event) => {
                            clearDraftFieldHighlight("middle_name");
                            replaceDraft({
                              ...verificationDraft,
                              biodata: {
                                ...verificationDraft.biodata,
                                middle_name: event.target.value,
                              },
                            });
                          }}
                          placeholder="Middle name"
                          autoCapitalize="words"
                          className={getDraftFieldClassName("middle_name", "h-12 bg-white/[0.05] text-xs")}
                        />
                      </VerificationField>
                      <VerificationField label="Surname">
                        <Input
                          value={verificationDraft.biodata.surname}
                          onChange={(event) => {
                            clearDraftFieldHighlight("surname");
                            replaceDraft({
                              ...verificationDraft,
                              biodata: {
                                ...verificationDraft.biodata,
                                surname: event.target.value,
                              },
                            });
                          }}
                          placeholder="Surname"
                          autoCapitalize="words"
                          className={getDraftFieldClassName("surname", "h-12 bg-white/[0.05] text-xs")}
                        />
                      </VerificationField>
                    </div>
                    <VerificationField label="Date of birth">
                      <Input
                        value={verificationDraft.biodata.date_of_birth}
                        onChange={(event) => {
                          clearDraftFieldHighlight("date_of_birth");
                          replaceDraft({
                            ...verificationDraft,
                            biodata: {
                              ...verificationDraft.biodata,
                              date_of_birth: event.target.value,
                            },
                          });
                        }}
                        type={draftDateOfBirthInputType}
                        onFocus={(event) => {
                          setDraftDateOfBirthInputType("date");
                          event.currentTarget.showPicker?.();
                        }}
                        onBlur={(event) => {
                          if (!event.currentTarget.value) {
                            setDraftDateOfBirthInputType("text");
                          }
                        }}
                        placeholder="Date of birth"
                        className={getDraftFieldClassName("date_of_birth", "h-12 bg-white/[0.05] text-xs")}
                      />
                    </VerificationField>
                    <div className="grid gap-3">
                      <VerificationField label="State of origin">
                        <select
                          value={verificationDraft.biodata.state_of_origin}
                          onChange={(event) => {
                            clearDraftFieldHighlight("state_of_origin");
                            replaceDraft({
                              ...verificationDraft,
                              biodata: {
                                ...verificationDraft.biodata,
                                state_of_origin: event.target.value,
                              },
                            });
                          }}
                          className={clsx(
                            getDraftFieldClassName(
                              "state_of_origin",
                              "h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-2 text-sm outline-none"
                            ),
                            verificationDraft.biodata.state_of_origin ? "text-white" : "text-zinc-400"
                          )}
                        >
                          <option value="" className="text-zinc-400">
                            State of origin
                          </option>
                          {NIGERIAN_STATES.map((state) => (
                            <option key={state} value={state}>
                              {state}
                            </option>
                          ))}
                        </select>
                      </VerificationField>
                      <VerificationField label="Country of birth">
                        <select
                          value={verificationDraft.biodata.country_of_birth}
                          onChange={(event) => {
                            clearDraftFieldHighlight("country_of_birth");
                            replaceDraft({
                              ...verificationDraft,
                              biodata: {
                                ...verificationDraft.biodata,
                                country_of_birth: event.target.value,
                              },
                            });
                          }}
                          className={clsx(
                            getDraftFieldClassName(
                              "country_of_birth",
                              "text-xs h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-2 text-sm outline-none"
                            ),
                            verificationDraft.biodata.country_of_birth ? "text-white" : "text-zinc-400"
                          )}
                        >
                          <option value="" className="text-zinc-400">
                            Country of birth
                          </option>
                          {WORLD_COUNTRIES.map((country) => (
                            <option key={country} value={country}>
                              {country}
                            </option>
                          ))}
                        </select>
                      </VerificationField>
                    </div>
                  </div>
                </Card>

                <Card className="grid gap-4 border-white/10 bg-black/10 p-5">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.10em] text-lime">NIN</p>
                    <h3 className="mt-2 font-display text-[16px] text-white">Identification Information</h3>
                  </div>
                  <div className="grid gap-3">
                    <VerificationField label="Gender">
                      <select
                        value={verificationDraft.biodata.gender}
                        onChange={(event) => {
                          clearDraftFieldHighlight("gender");
                          replaceDraft({
                            ...verificationDraft,
                            biodata: {
                              ...verificationDraft.biodata,
                              gender: event.target.value,
                            },
                          });
                        }}
                        className={clsx(
                          getDraftFieldClassName(
                            "gender",
                            "text-xs h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-4 text-sm outline-none"
                          ),
                          verificationDraft.biodata.gender ? "text-white" : "text-zinc-400"
                        )}
                      >
                        <option value="" className="text-zinc-400">
                          Select gender
                        </option>
                        {CORPER_GENDERS.filter((option) => option.value !== "other").map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </VerificationField>
                    <VerificationField label="Mobile number">
                      <Input
                        value={verificationDraft.biodata.mobile_number}
                        onChange={(event) => {
                          clearDraftFieldHighlight("mobile_number");
                          replaceDraft({
                            ...verificationDraft,
                            biodata: {
                              ...verificationDraft.biodata,
                              mobile_number: normalizeMobileNumber(event.target.value),
                            },
                          });
                        }}
                        placeholder="Number linked to NIN e.g. +234.. or 0.."
                        inputMode="tel"
                        maxLength={14}
                        className={getDraftFieldClassName("mobile_number", "h-12 bg-white/[0.05] text-xs")}
                      />
                    </VerificationField>
                  </div>
                  <VerificationField label="University matriculation number">
                    <Input
                      value={verificationDraft.biodata.university_matriculation_number}
                      onChange={(event) => {
                        clearDraftFieldHighlight("university_matriculation_number");
                        replaceDraft({
                          ...verificationDraft,
                          biodata: {
                            ...verificationDraft.biodata,
                            university_matriculation_number: event.target.value,
                          },
                        });
                      }}
                      placeholder="University matric number"
                      autoCapitalize="characters"
                      maxLength={16}
                      className={getDraftFieldClassName(
                        "university_matriculation_number",
                        "h-12 bg-white/[0.05] text-xs"
                      )}
                    />
                  </VerificationField>
                  <VerificationField label="NIN">
                    <Input
                      value={verificationDraft.nin.submitted_value}
                      onChange={(event) => {
                        clearDraftFieldHighlight("nin");
                        replaceDraft({
                          ...verificationDraft,
                          nin: {
                            submitted_value: event.target.value,
                          },
                        });
                      }}
                      placeholder="Enter your 11-digit NIN"
                      inputMode="numeric"
                      maxLength={11}
                      className={getDraftFieldClassName("nin", "h-12 bg-white/[0.05] text-xs")}
                    />
                  </VerificationField>
                </Card>

                <Card className="grid gap-4 border-white/10 bg-black/10 p-5">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.10em] text-lime">NYSC call-up</p>
                    <h3 className="mt-2 font-display text-[16px] text-white">NYSC Call-up number & document</h3>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem]">
                    <VerificationField label="Call-up number">
                      <Input
                        value={verificationDraft.callup.submitted_value}
                        onChange={(event) => {
                          clearDraftFieldHighlight("callup");
                          replaceDraft({
                            ...verificationDraft,
                            callup: {
                              ...verificationDraft.callup,
                              submitted_value: normalizeNyscCallupNumber(event.target.value),
                            },
                          });
                        }}
                        placeholder="e.g NYSC/LAG/2025/54321"
                        autoCapitalize="characters"
                        maxLength={20}
                        pattern="NYSC/[A-Z]{3}/\\d{4}/\\d{4,6}"
                        className={getDraftFieldClassName("callup", "h-12 bg-white/[0.05] text-xs")}
                      />
                    </VerificationField>
                    <VerificationField label="Document">
                      <label
                        className={getDraftFieldClassName(
                          "callup_document",
                          "grid h-12 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-2xl border border-dashed border-white/15 bg-white/[0.05] px-4 text-sm text-white transition hover:border-lime/40 hover:bg-white/[0.05]"
                        )}
                      >
                        <FileText className="h-4 w-4 text-lime" />
                        <span className="truncate text-xs text-white/72">
                          {verificationDraft.callup.document?.name ||
                            verificationDraft.callup.document_name ||
                            "Upload doc"}
                        </span>
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png,.webp"
                          className="sr-only"
                          onChange={(event) => {
                            const file = event.target.files?.[0] ?? null;
                            clearDraftFieldHighlight("callup_document");
                            replaceDraft({
                              ...verificationDraft,
                              callup: {
                                ...verificationDraft.callup,
                                document: file,
                                document_name: file?.name ?? "",
                              },
                            });
                          }}
                        />
                      </label>
                    </VerificationField>
                  </div>
                </Card>

                <Card className="grid gap-4 border-white/10 bg-black/10 p-5">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.10em] text-lime">NYSC state code</p>
                    <h3 className="mt-2 font-display text-[16px] text-white">NYSC State code & document</h3>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem]">
                    <VerificationField label="State code">
                      <Input
                        value={verificationDraft.state_code.submitted_value}
                        onChange={(event) => {
                          clearDraftFieldHighlight("state_code");
                          replaceDraft({
                            ...verificationDraft,
                            state_code: {
                              ...verificationDraft.state_code,
                              submitted_value: normalizeNyscStateCode(event.target.value),
                            },
                          });
                        }}
                        placeholder="e.g NYSC/LG/26B/72673"
                        autoCapitalize="characters"
                        maxLength={18}
                        pattern="NYSC/[A-Z]{2}/\\d{2}[A-C]/\\d{5,6}"
                        className={getDraftFieldClassName("state_code", "h-12 bg-white/[0.05] text-xs")}
                      />
                    </VerificationField>
                    <VerificationField label="Document">
                      <label
                        className={getDraftFieldClassName(
                          "state_code_document",
                          "grid h-12 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-2xl border border-dashed border-white/15 bg-white/[0.05] px-4 text-sm text-white transition hover:border-lime/40 hover:bg-white/[0.05]"
                        )}
                      >
                        <FileText className="h-4 w-4 text-lime" />
                        <span className="truncate text-xs text-white/72">
                          {verificationDraft.state_code.document?.name ||
                            verificationDraft.state_code.document_name ||
                            "Upload doc"}
                        </span>
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png,.webp"
                          className="sr-only"
                          onChange={(event) => {
                            const file = event.target.files?.[0] ?? null;
                            clearDraftFieldHighlight("state_code_document");
                            replaceDraft({
                              ...verificationDraft,
                              state_code: {
                                ...verificationDraft.state_code,
                                document: file,
                                document_name: file?.name ?? verificationDraft.state_code.document_name,
                              },
                            });
                          }}
                        />
                      </label>
                    </VerificationField>
                  </div>
                </Card>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-white/10 bg-black/12 p-4">
                <div className="grid gap-1 text-xs text-white/60">
                  <PpaDisclaimerNote className="max-w-[36rem] text-[11px] leading-5 text-white/55" />
                </div>
                <Button type="button" onClick={handleProceedToLegalDocuments}>
                  Submit
                </Button>
              </div>
            </Card>
          ) : (
            <VerificationOverviewSkeleton />
          )
        ) : (
          <Card className="relative overflow-hidden border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.12),rgba(4,21,15,0.08)),radial-gradient(circle_at_top_right,rgba(124,217,161,0.28),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(244,211,94,0.14),transparent_36%),linear-gradient(180deg,#163F2D_0%,#0A2117_100%)] p-0 animate-[chat-panel-in_450ms_ease-out]">
            <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_50%)] lg:block" />
            <div className="relative grid gap-6 p-6 lg:p-8">
              <div className="max-w-2xl">
                <h2 className="font-display text-3xl leading-tight text-white sm:text-[2.2rem]">
                  {heroCopy.title}
                </h2>
                <p className="mt-4 max-w-[46rem] text-sm leading-7 text-white/78">
                  {heroCopy.description}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-[24px] border border-white/10 bg-black/10 p-4 backdrop-blur-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-lime">Approved</p>
                  <p className="mt-3 font-display text-2xl text-white">
                    {completedDocumentsCount}/{verificationDocuments.length}
                  </p>
                  <p className="mt-2 text-sm text-mist">Number of documents reviewed</p>
                </div>

                <div className="rounded-[24px] border border-white/10 bg-black/10 p-4 backdrop-blur-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-lime">Attempts</p>
                  <p className="mt-3 font-display text-2xl text-white">{sortedAttempts.length}</p>
                  <p className="mt-2 text-sm text-mist">Submission attempts made.</p>
                </div>

                <div className="rounded-[24px] border border-white/10 bg-black/10 p-4 backdrop-blur-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-lime">Next step</p>
                  <p className="mt-3 font-display text-xl text-white">{nextStep}</p>
                  <p className="mt-2 text-sm text-mist">
                    {documentsVerified
                      ? "Credentials verified, continue with profile update."
                      : "All four verification cards are required before profile unlocks."}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        )}

        {false ? (
          <div id="document-checks" className="grid gap-5 xl:grid-cols-2">
            {isInitialProfileLoad
              ? verificationDocuments.map((document) => <VerificationCardSkeleton key={document.type} />)
              : verificationDocuments.map((document, index) => {
                const status = getDocumentStatus(profile.data, document.type);
                const statusMeta = getStatusMeta(status);
                const latestAttempt = latestAttemptByType[document.type];
                const storedValue = getStoredMaskedValue(profile.data, document.type);
                const uploadedDocument = getUploadedDocument(profile.data, document.type);
                const uploadedDocumentUrl = resolveMediaUrl(uploadedDocument);
                const normalizedDocumentStatus = normalizeStatus(status);
                const canSubmit = canSubmitDocument(normalizedDocumentStatus);
                const showSubmissionForm = canSubmit && normalizedDocumentStatus !== "pending";
                const buttonState = getSubmissionButtonState(
                  status,
                  submittingType === document.type
                );
                const DocumentIcon = document.icon;

                return (
                  <Card
                    key={document.type}
                    className={clsx(
                      "relative overflow-hidden p-0 animate-[chat-bubble-in_520ms_ease-out]",
                      statusMeta.panelClass,
                      index === 1 ? "[animation-delay:120ms]" : ""
                    )}
                  >
                    <div className="absolute inset-x-0 top-0 h-24 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.1),transparent_65%)]" />
                    <div className="relative flex h-full flex-col gap-6 p-6">
                      <div className="flex items-start justify-between gap-4">
                        <div
                          className={clsx(
                            "flex h-14 w-14 items-center justify-center rounded-[20px] border",
                            statusMeta.iconClass
                          )}
                        >
                          <DocumentIcon className="h-6 w-6" />
                        </div>
                        <Badge className={statusMeta.badgeClass}>{statusMeta.label}</Badge>
                      </div>

                      <div>
                        <p className="text-xs uppercase tracking-[0.22em] text-lime">{document.label}</p>
                        <h2 className="mt-3 font-display text-2xl text-white">{document.title}</h2>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-[24px] border border-white/10 bg-black/10 p-4">
                          <p className="text-xs uppercase tracking-[0.122em] text-white/50">Current status</p>
                          <p
                            className={clsx(
                              "mt-3 text-xs",
                              normalizedDocumentStatus === "verified" ? "text-lime" : "text-white"
                            )}
                          >
                            {statusMeta.label}
                          </p>
                        </div>
                        <div className="rounded-[24px] border border-white/10 bg-black/10 p-4">
                          <p className="text-xs uppercase tracking-[0.12em] text-white/50">
                            {storedValue ? "Stored value" : latestAttempt ? "Last submission" : "Document record"}
                          </p>
                          <p className="mt-3 text-xs text-white">
                            {storedValue || latestAttempt?.submitted_value_masked || "Nothing submitted yet"}
                          </p>
                        </div>
                      </div>

                      {showSubmissionForm ? (
                        document.type === "biodata" ? (
                          <form
                            action={handleBiodataSubmit}
                            className="mt-auto grid gap-4 rounded-[24px] border border-white/10 bg-black/12 p-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="text-xs uppercase tracking-[0.18em] text-lime">
                                  {status === "rejected" ? "Resubmit biodata" : "Submit biodata"}
                                </p>
                              </div>
                              {latestAttempt ? (
                                <p className="text-[11px] uppercase tracking-[0.16em] text-white/40">
                                  Latest {formatVerificationStatus(latestAttempt.status)}
                                </p>
                              ) : null}
                            </div>

                            <div className="grid gap-3">
                              <div className="grid gap-3 md:grid-cols-3">
                                <VerificationField label="First name">
                                  <Input
                                    name="first_name"
                                    placeholder="First name"
                                    required
                                    autoCapitalize="words"
                                    defaultValue={profile.data?.first_name ?? ""}
                                    className="h-12 bg-white/[0.05] text-xs"
                                  />
                                </VerificationField>
                                <VerificationField label="Middle name">
                                  <Input
                                    name="middle_name"
                                    placeholder="Middle name"
                                    autoCapitalize="words"
                                    defaultValue={profile.data?.middle_name ?? ""}
                                    className="h-12 bg-white/[0.05] text-xs"
                                  />
                                </VerificationField>
                                <VerificationField label="Surname">
                                  <Input
                                    name="surname"
                                    placeholder="Surname"
                                    required
                                    autoCapitalize="words"
                                    defaultValue={profile.data?.surname ?? ""}
                                    className="h-12 bg-white/[0.05] text-xs"
                                  />
                                </VerificationField>
                              </div>
                              <VerificationField label="Date of birth">
                                <Input
                                  name="date_of_birth"
                                  type={profileDateOfBirthInputType}
                                  onFocus={(event) => {
                                    setProfileDateOfBirthInputType("date");
                                    event.currentTarget.showPicker?.();
                                  }}
                                  onBlur={(event) => {
                                    if (!event.currentTarget.value) {
                                      setProfileDateOfBirthInputType("text");
                                    }
                                  }}
                                  placeholder="Date of birth"
                                  required
                                  defaultValue={profile.data?.date_of_birth ?? ""}
                                  className="h-12 bg-white/[0.05] text-xs"
                                />
                              </VerificationField>
                              <div className="grid gap-3 md:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
                                <VerificationField label="Gender">
                                  <select
                                    name="gender"
                                    value={profileGenderValue}
                                    onChange={(event) => setProfileGenderValue(event.target.value)}
                                    required
                                    className={clsx(
                                      "h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-4 text-sm outline-none",
                                      profileGenderValue ? "text-white" : "text-zinc-400"
                                    )}
                                  >
                                    <option value="" className="text-zinc-400">
                                      Select gender
                                    </option>
                                    {CORPER_GENDERS.filter((option) => option.value !== "other").map((option) => (
                                      <option key={option.value} value={option.value}>
                                        {option.label}
                                      </option>
                                    ))}
                                  </select>
                                </VerificationField>
                                <VerificationField label="Mobile number">
                                  <Input
                                    name="mobile_number"
                                    placeholder="+2348012345678"
                                    inputMode="tel"
                                    maxLength={14}
                                    required
                                    defaultValue={profile.data?.mobile_number ?? ""}
                                    className="h-12 bg-white/[0.05] text-xs"
                                  />
                                </VerificationField>
                              </div>
                              <div className="grid gap-5 md:grid-cols-2">
                                <VerificationField label="State of origin">
                                  <select
                                    name="state_of_origin"
                                    value={profileStateOfOriginValue}
                                    onChange={(event) => setProfileStateOfOriginValue(event.target.value)}
                                    className={clsx(
                                      "h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-4 text-sm outline-none",
                                      profileStateOfOriginValue ? "text-white" : "text-zinc-400"
                                    )}
                                  >
                                    <option value="" className="text-zinc-400">
                                      State of origin
                                    </option>
                                    {NIGERIAN_STATES.map((state) => (
                                      <option key={state} value={state}>
                                        {state}
                                      </option>
                                    ))}
                                  </select>
                                </VerificationField>
                                <VerificationField label="Country of birth">
                                  <select
                                    name="country_of_birth"
                                    defaultValue={profile.data?.country_of_birth ?? ""}
                                    className={clsx(
                                      "h-12 rounded-2xl border border-white/10 bg-white/[0.05] px-2 text-sm outline-none",
                                      profile.data?.country_of_birth ? "text-white" : "text-zinc-400"
                                    )}
                                  >
                                    <option value="" className="text-zinc-400">
                                      Country of birth
                                    </option>
                                    {WORLD_COUNTRIES.map((country) => (
                                      <option key={country} value={country}>
                                        {country}
                                      </option>
                                    ))}
                                  </select>
                                </VerificationField>
                              </div>
                              <VerificationField label="University matriculation number">
                                <Input
                                  name="university_matriculation_number"
                                  placeholder="Enter your matric number"
                                  autoCapitalize="characters"
                                  maxLength={16}
                                  pattern="[A-Za-z0-9/]{8,16}"
                                  defaultValue={profile.data?.university_matriculation_number ?? ""}
                                  className="h-12 bg-white/[0.05] text-xs"
                                />
                              </VerificationField>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="text-xs text-white/55">Matric number is optional. If provided, use 8 to 16 characters with letters, numbers, and &quot;/&quot; only.</p>
                              <div className="grid justify-items-end gap-2">
                                <Button
                                  type="submit"
                                  disabled={buttonState.disabled}
                                  className={clsx("min-w-[190px]", buttonState.className)}
                                >
                                  {buttonState.label}
                                </Button>
                                <PpaDisclaimerNote className="max-w-[24rem] text-right text-[11px] leading-5 text-white/55" />
                              </div>
                            </div>
                          </form>
                        ) : (
                          <form
                            action={(formData) => handleDocumentSubmit(document.type, formData)}
                            className="mt-auto grid gap-4 rounded-[24px] border border-white/10 bg-black/12 p-4"
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div>
                                <p className="text-xs uppercase tracking-[0.18em] text-lime">
                                  {status === "rejected" ? "Resubmit document" : "Submit document"}
                                </p>
                              </div>
                              {latestAttempt ? (
                                <p className="text-[11px] uppercase tracking-[0.16em] text-white/40">
                                  Latest {formatVerificationStatus(latestAttempt.status)}
                                </p>
                              ) : null}
                            </div>

                            {supportsDocumentUpload(document.type) ? (
                              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem]">
                                <VerificationField
                                  label={document.type === "callup" ? "Call-up number" : "State code"}
                                >
                                  <Input
                                    name="submitted_value"
                                    placeholder={document.placeholder}
                                    required
                                    maxLength={document.maxLength}
                                    inputMode="text"
                                    autoCapitalize="characters"
                                    pattern={
                                      document.type === "callup"
                                        ? "NYSC/[A-Za-z]{3}/\\d{4}/\\d{4,6}"
                                        : "NYSC/[A-Za-z]{2}/\\d{2}[A-Ca-c]/\\d{5,6}"
                                    }
                                    className="h-12 bg-white/[0.05] text-xs"
                                  />
                                </VerificationField>
                                <VerificationField label="Document">
                                  <label className="grid h-12 cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-2xl border border-dashed border-white/15 bg-white/[0.05] px-4 text-sm text-white transition hover:border-lime/40 hover:bg-white/[0.05]">
                                    <FileText className="h-4 w-4 text-lime" />
                                    <span
                                      className={clsx(
                                        "truncate text-xs",
                                        selectedDocuments[document.type]?.name || getDocumentFileName(uploadedDocument)
                                          ? "text-white/72"
                                          : "text-zinc-400"
                                      )}
                                    >
                                      {selectedDocuments[document.type]?.name ||
                                        getDocumentFileName(uploadedDocument) ||
                                        "Upload doc"}
                                    </span>
                                    <input
                                      key={`${document.type}-${documentInputVersion[document.type]}`}
                                      name="document"
                                      type="file"
                                      accept=".pdf,.jpg,.jpeg,.png,.webp"
                                      required
                                      className="sr-only"
                                      onChange={(event) => {
                                        const file = event.target.files?.[0] ?? null;
                                        setSelectedDocuments((current) => ({
                                          ...current,
                                          [document.type]: file,
                                        }));
                                      }}
                                    />
                                  </label>
                                </VerificationField>
                              </div>
                            ) : (
                              <VerificationField label={document.label}>
                                <Input
                                  name="submitted_value"
                                  placeholder={document.placeholder}
                                  required
                                  maxLength={document.maxLength}
                                  inputMode={document.type === "nin" ? "numeric" : "text"}
                                  autoCapitalize={document.type === "nin" ? "none" : "characters"}
                                  pattern={
                                    document.type === "nin"
                                      ? "\\d{11}"
                                      : document.type === "callup"
                                        ? "NYSC/[A-Za-z]{3}/\\d{4}/\\d{4,6}"
                                        : "NYSC/[A-Za-z]{2}/\\d{2}[A-Ca-c]/\\d{5,6}"
                                  }
                                  className="h-12 bg-white/[0.05] text-xs"
                                />
                              </VerificationField>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div className="grid gap-1 text-xs text-white/55">
                                <p>
                                  {document.type === "nin"
                                    ? "We only accept the 11-digit NIN format."
                                    : document.type === "callup"
                                      ? "format: e.g. NYSC/ABC/2024/1234 as in your call-up letter."
                                      : "format: e.g. NYSC/LG/26B/72673 assigned during orientation."}
                                </p>
                                {supportsDocumentUpload(document.type) ? (
                                  uploadedDocumentUrl ? (
                                    <a
                                      href={uploadedDocumentUrl}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-lime transition hover:text-white"
                                    >
                                      View uploaded document
                                    </a>
                                  ) : (
                                    <p>upload a PDF, JPG, PNG, or WebP file up to 5MB.</p>
                                  )
                                ) : null}
                              </div>
                              <div className="grid justify-items-end gap-2">
                                <Button
                                  type="submit"
                                  disabled={buttonState.disabled}
                                  className={clsx("min-w-[190px]", buttonState.className)}
                                >
                                  {buttonState.label}
                                </Button>
                                <PpaDisclaimerNote className="max-w-[24rem] text-right text-[11px] leading-5 text-white/55" />
                              </div>
                            </div>
                          </form>
                        )
                      ) : (
                        <div
                          className={clsx(
                            "mt-auto grid gap-3 rounded-[24px] p-4",
                            normalizedDocumentStatus === "pending"
                              ? "border border-[#8A5A2B]/35 bg-[#8A5A2B]/12"
                              : "border border-lime/20 bg-lime/10"
                          )}
                        >
                          <div className="grid gap-1">
                            <p className="text-sm font-semibold text-white">
                              {normalizedDocumentStatus === "pending"
                                ? "Submission received."
                                : document.type === "biodata"
                                  ? "Biodata approved."
                                  : "Document approved."}
                            </p>
                            <p className="text-xs text-mist">
                              {normalizedDocumentStatus === "pending"
                                ? "Your credential is waiting for admin review."
                                : "No further action is needed for this record."}
                            </p>
                            {uploadedDocumentUrl ? (
                              <a
                                href={uploadedDocumentUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs font-semibold text-lime transition hover:text-white"
                              >
                                View uploaded document
                              </a>
                            ) : null}
                          </div>
                          <div className="flex items-center justify-between gap-4">
                            <Button
                              type="button"
                              disabled
                              className={clsx("min-w-[190px]", buttonState.className)}
                            >
                              {buttonState.label}
                            </Button>
                            {normalizedDocumentStatus === "pending" ? (
                              <Clock3 className="h-6 w-6 shrink-0 text-[#C68C4B]" />
                            ) : (
                              <CheckCircle2 className="h-6 w-6 shrink-0 text-lime" />
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </Card>
                );
              })}
          </div>
        ) : null}

        <Card
          id="verification-activity"
          className="overflow-hidden border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(4,21,15,0.04)),linear-gradient(180deg,rgba(11,38,27,0.92),rgba(7,20,14,0.96))] p-0 animate-[chat-panel-in_650ms_ease-out]"
        >
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 px-6 py-5">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Recent activity</p>
              <h2 className="mt-3 font-display text-2xl text-white">Submission history</h2>
              <p className="mt-2 text-sm text-mist">
                Every attempt appears here with a masked value and the latest review outcome.
              </p>
            </div>
            <Badge className="border-white/12 bg-white/[0.05] text-white">{sortedAttempts.length} attempts</Badge>
          </div>

          {isInitialAttemptsLoad ? (
            <div className="grid gap-3 px-6 py-6">
              <Skeleton className="h-20 w-full rounded-[24px]" />
              <Skeleton className="h-20 w-full rounded-[24px]" />
              <Skeleton className="h-20 w-full rounded-[24px]" />
            </div>
          ) : sortedAttempts.length ? (
            <div className="divide-y divide-white/10">
              {sortedAttempts.map((attempt) => {
                const attemptDisplayStatus = getAttemptDisplayStatus(profile.data ?? null, attempt);
                const attemptStatus = getStatusMeta(attemptDisplayStatus, attempt.review_note);
                const AttemptIcon = attempt.verification_type === "nin" ? Fingerprint : FileText;

                return (
                  <div
                    key={attempt.id}
                    className="grid gap-4 px-6 py-5 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-center"
                  >
                    <div className="flex min-w-0 items-start gap-4">
                      <div
                        className={clsx(
                          "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border",
                          attemptStatus.iconClass
                        )}
                      >
                        <AttemptIcon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-white">
                            {formatVerificationType(attempt.verification_type)}
                          </p>
                          <p className="text-[11px] uppercase tracking-[0.16em] text-white/40">
                            {attempt.submitted_value_masked}
                          </p>
                        </div>
                        <p className="mt-2 text-sm text-mist">{attemptStatus.description}</p>
                        {attempt.review_note && normalizeStatus(attemptDisplayStatus) !== "failed" ? (
                          <p className="mt-2 text-xs leading-6 text-white/55">Note: {attempt.review_note}</p>
                        ) : null}
                      </div>
                    </div>
                    <div className="justify-self-start md:justify-self-center">
                      <Badge className={attemptStatus.badgeClass}>{attemptStatus.label}</Badge>
                    </div>
                    <p className="text-xs uppercase tracking-[0.18em] text-white/45">
                      {formatDateTime(attempt.created_at)}
                    </p>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="px-6 py-12 text-center">
              <p className="font-display text-xl text-white">No verification attempts yet</p>
              <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-mist">
                Submit your verification credentials an the result will appear here with the latest review outcome.
              </p>
            </div>
          )}
        </Card>
      </div>
    </DashboardShell>
  );
}
