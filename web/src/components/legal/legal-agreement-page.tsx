"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { useCorperVerificationDraft } from "@/components/providers/corper-verification-draft-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useApiQuery } from "@/hooks/use-api-query";
import {
  formatAgreementDate,
  hydrateLegalDocumentContent,
  type LegalDocumentRecord,
} from "@/lib/legal-document-template";
import { ApiError, apiFetch } from "@/lib/api";
import { MarkdownRenderer } from "@/components/legal/markdown-renderer";
import { PpaDisclaimerNote } from "@/components/legal/ppa-disclaimer-note";

type LegalAcceptanceMap = Record<
  string,
  {
    accepted_at?: string;
    signer_name?: string;
  }
>;

type TermsProfile = {
  id: string;
  full_name?: string;
  company_name?: string;
  email?: string;
  verification_status?: string;
  approval_status?: string;
  is_complete: boolean;
  profile_fields_complete: boolean;
  verification_fields_complete?: boolean;
  terms_accepted: boolean;
  nysc_callup_number?: string;
  nysc_state_code?: string;
  nysc_callup_document?: string | null;
  nysc_state_code_document?: string | null;
  biodata_verification_status?: string;
  nin_verification_status?: string;
  nysc_callup_verification_status?: string;
  nysc_state_code_verification_status?: string;
  legal_acceptances?: LegalAcceptanceMap;
};

function corperDocumentsAlreadyVerified(profile: TermsProfile | null | undefined) {
  if (!profile) {
    return false;
  }

  return (
    profile.biodata_verification_status === "verified" &&
    profile.nin_verification_status === "verified" &&
    profile.nysc_callup_verification_status === "verified" &&
    profile.nysc_state_code_verification_status === "verified"
  );
}

function hasExistingCorperVerificationStatus(status: string | undefined) {
  return Boolean(status && status !== "unsubmitted");
}

function LegalDocumentAcceptanceCard({
  accepted,
  checked,
  legalDocument,
  onCheckedChange,
}: {
  accepted: boolean;
  checked: boolean;
  legalDocument: LegalDocumentRecord;
  onCheckedChange: (checked: boolean) => void;
}) {
  const [hasReachedEnd, setHasReachedEnd] = useState(accepted);

  useEffect(() => {
    if (accepted) {
      setHasReachedEnd(true);
    }
  }, [accepted]);

  useEffect(() => {
    if (accepted) {
      return;
    }

    const container = globalThis.document.getElementById(`legal-document-scroll-${legalDocument.slug}`);
    if (!(container instanceof HTMLDivElement)) {
      return;
    }

    const updateScrollState = () => {
      const hasScrollableOverflow = container.scrollHeight - container.clientHeight > 4;
      if (!hasScrollableOverflow) {
        setHasReachedEnd(true);
        return;
      }

      const isAtEnd = container.scrollTop + container.clientHeight >= container.scrollHeight - 4;
      setHasReachedEnd(isAtEnd);
    };

    updateScrollState();
    container.addEventListener("scroll", updateScrollState, { passive: true });
    window.addEventListener("resize", updateScrollState);

    return () => {
      container.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [accepted, legalDocument.slug]);

  const checkboxEnabled = accepted || hasReachedEnd;

  return (
    <Card className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="grid gap-1">
          <p className="text-xs uppercase tracking-[0.22em] text-lime">{legalDocument.slug}</p>
          <h3 className="font-display text-2xl text-white">{legalDocument.title}</h3>
        </div>
        <Link
          href={`/legal/${legalDocument.slug}`}
          target="_blank"
          className="text-sm font-semibold text-lime hover:text-white"
        >
          Open full page
        </Link>
      </div>
      <div
        id={`legal-document-scroll-${legalDocument.slug}`}
        className="max-h-[26rem] overflow-y-auto rounded-[24px] border border-white/10 bg-white/[0.03] p-5"
      >
        <MarkdownRenderer content={legalDocument.content} mode="signing" />
      </div>
      <div className="grid gap-1.5">
        <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-white/45">
          Agreement confirmation
        </p>
        {!checkboxEnabled ? (
          <p className="text-xs text-mist">Scroll to the end of this document to enable the checkbox.</p>
        ) : null}
        <label className="inline-flex items-start gap-3 text-sm text-white">
          <input
            type="checkbox"
            checked={checked || accepted}
            disabled={!checkboxEnabled}
            onChange={(event) => onCheckedChange(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-white/20 bg-transparent accent-[#1FB766]"
          />
          <span>I have read and agree to this document.</span>
        </label>
      </div>
    </Card>
  );
}

const roleConfig = {
  corper: {
    title: "Legal Agreements",
    endpoint: "/corpers/me/",
    submitEndpoint: "/corpers/me/submit/",
    successRedirect: "/corper/profile",
    backHref: "/corper/verification",
    submitMessage: "Verification Successful and legal agreements recorded. You can now complete your profile",
    reviewTitle: "Review and accept legal terms of service and corpershub policies to continue",
    allowSubmitWithoutProfileCompletion: true,
  },
  company: {
    title: "Legal Agreements",
    endpoint: "/companies/me/",
    submitEndpoint: "/companies/me/submit/",
    successRedirect: "/company/profile",
    backHref: "/company/verification",
    submitMessage: "Company verification successful and legal agreements recorded. You can now complete your profile.",
    reviewTitle: "Review and accept legal terms of service and corpershub policies to continue",
    allowSubmitWithoutProfileCompletion: false,
  },
} as const;

const GENERIC_CORPER_VERIFICATION_ERROR =
  "Unable to submit verification right now. Please try again.";

function hasPendingCorperVerificationDraft(draft: ReturnType<typeof useCorperVerificationDraft>["draft"]) {
  return Boolean(
    draft.biodata.first_name.trim() &&
    draft.biodata.middle_name.trim() &&
    draft.biodata.surname.trim() &&
    draft.biodata.date_of_birth &&
    draft.biodata.gender.trim() &&
    draft.biodata.mobile_number.trim() &&
    draft.biodata.state_of_origin.trim() &&
    draft.biodata.country_of_birth.trim() &&
    draft.nin.submitted_value.trim() &&
    draft.callup.submitted_value.trim() &&
    draft.state_code.submitted_value.trim()
  );
}

function resolveSuccessRedirect(role: "corper" | "company", profile: TermsProfile) {
  if (role === "company") {
    return "/company/profile";
  }

  return corperDocumentsAlreadyVerified(profile) ? "/corper/profile" : "/corper/verification";
}

function extractNestedErrorMessage(value: unknown): string {
  if (!value) {
    return "";
  }

  if (typeof value === "string") {
    return value.trim();
  }

  if (Array.isArray(value)) {
    for (const entry of value) {
      const message = extractNestedErrorMessage(entry);
      if (message) {
        return message;
      }
    }
    return "";
  }

  if (typeof value !== "object") {
    return "";
  }

  const record = value as Record<string, unknown>;
  for (const key of ["review_note", "error", "message", "detail"]) {
    const message = extractNestedErrorMessage(record[key]);
    if (message) {
      return message;
    }
  }

  for (const key of ["attempt", "metadata"]) {
    const message = extractNestedErrorMessage(record[key]);
    if (message) {
      return message;
    }
  }

  for (const entry of Object.values(record)) {
    const message = extractNestedErrorMessage(entry);
    if (message) {
      return message;
    }
  }

  return "";
}

function humanizeVerificationErrorMessage(message: string): string {
  const normalizedMessage = message.trim();
  if (!normalizedMessage) {
    return "";
  }

  if (
    normalizedMessage.includes("does not match the NIN record") ||
    normalizedMessage.includes("No NIN record was found") ||
    normalizedMessage.includes("already been submitted") ||
    normalizedMessage.includes("already been verified") ||
    normalizedMessage.includes("previously deleted account")
  ) {
    return normalizedMessage;
  }

  if (/Key \(mobile_number\)=\([^)]+\) already exists/i.test(normalizedMessage)) {
    return "This mobile number has already been submitted.";
  }

  if (/Key \(university_matriculation_number\)=\([^)]+\) already exists/i.test(normalizedMessage)) {
    return "This university matriculation number has already been submitted.";
  }

  if (/Key \(nin_lookup_hash\)=\([^)]+\) already exists/i.test(normalizedMessage)) {
    return "This NIN number has already been submitted.";
  }

  if (/Key \(nysc_callup_lookup_hash\)=\([^)]+\) already exists/i.test(normalizedMessage)) {
    return "This NYSC call-up number has already been submitted.";
  }

  if (/Key \(nysc_state_code_lookup_hash\)=\([^)]+\) already exists/i.test(normalizedMessage)) {
    return "This NYSC state code has already been submitted.";
  }

  return normalizedMessage;
}

function getLegalAgreementErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const bodyMessage = humanizeVerificationErrorMessage(extractNestedErrorMessage(error.body));
    if (bodyMessage && bodyMessage !== GENERIC_CORPER_VERIFICATION_ERROR) {
      return bodyMessage;
    }

    const errorMessage = humanizeVerificationErrorMessage(error.message);
    if (errorMessage) {
      return errorMessage;
    }
  }

  if (error instanceof Error) {
    const errorMessage = humanizeVerificationErrorMessage(error.message);
    if (errorMessage) {
      return errorMessage;
    }
  }

  return GENERIC_CORPER_VERIFICATION_ERROR;
}

export function LegalAgreementPage({
  role,
  documents,
}: {
  role: "corper" | "company";
  documents: LegalDocumentRecord[];
}) {
  const router = useRouter();
  const { hydrated, session, updateSession } = useAuth();
  const { draft: verificationDraft, clearDraft } = useCorperVerificationDraft();
  const config = roleConfig[role];
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === role;
  const profile = useApiQuery<TermsProfile>(config.endpoint, protectedQueryEnabled);
  const [checkedDocuments, setCheckedDocuments] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const hasVerificationDraft = role === "corper" && hasPendingCorperVerificationDraft(verificationDraft);
  const shouldUseVerificationDraft = role === "corper" && !profile.data?.terms_accepted;

  useEffect(() => {
    if (profile.data?.terms_accepted) {
      clearDraft();
    }
  }, [clearDraft, profile.data?.terms_accepted]);

  const signerName =
    role === "company"
      ? profile.data?.company_name?.trim() || session?.user.email || ""
      : shouldUseVerificationDraft
        ? [
          verificationDraft.biodata.first_name,
          verificationDraft.biodata.middle_name,
          verificationDraft.biodata.surname,
        ]
          .map((value) => value.trim())
          .filter(Boolean)
          .join(" ") ||
        profile.data?.full_name?.trim() ||
        session?.user.email ||
        ""
        : profile.data?.full_name?.trim() || session?.user.email || "";
  const agreementDate = formatAgreementDate();
  const resolvedDocuments = useMemo(
    () =>
      documents.map((document) => ({
        ...document,
        content: hydrateLegalDocumentContent(document.content, {
          name: signerName,
          company_name: profile.data?.company_name ?? "",
          date: agreementDate,
          nysc_callup_number:
            shouldUseVerificationDraft
              ? verificationDraft.callup.submitted_value || profile.data?.nysc_callup_number || ""
              : profile.data?.nysc_callup_number ?? "",
          nysc_state_code:
            shouldUseVerificationDraft
              ? verificationDraft.state_code.submitted_value || profile.data?.nysc_state_code || ""
              : profile.data?.nysc_state_code ?? "",
        }),
      })),
    [
      agreementDate,
      documents,
      profile.data?.company_name,
      shouldUseVerificationDraft,
      verificationDraft.callup.submitted_value,
      verificationDraft.state_code.submitted_value,
      profile.data?.nysc_callup_number,
      profile.data?.nysc_state_code,
      session?.user.email,
      signerName,
    ]
  );
  const acceptedDocuments = profile.data?.legal_acceptances ?? {};
  const allDocumentsChecked = resolvedDocuments.every(
    (document) => checkedDocuments[document.slug] || Boolean(acceptedDocuments[document.slug])
  );
  const canSubmitProfile =
    role === "company"
      ? Boolean(profile.data?.verification_fields_complete)
      : config.allowSubmitWithoutProfileCompletion || Boolean(profile.data?.profile_fields_complete);

  async function submitCorperVerificationDraft() {
    if (corperDocumentsAlreadyVerified(profile.data)) {
      return;
    }

    const hasStoredBiodataVerification = hasExistingCorperVerificationStatus(
      profile.data?.biodata_verification_status
    );
    const hasStoredNinVerification = hasExistingCorperVerificationStatus(
      profile.data?.nin_verification_status
    );
    const hasStoredCallupVerification =
      hasExistingCorperVerificationStatus(profile.data?.nysc_callup_verification_status) ||
      Boolean(profile.data?.nysc_callup_document);
    const hasStoredStateCodeVerification =
      hasExistingCorperVerificationStatus(profile.data?.nysc_state_code_verification_status) ||
      Boolean(profile.data?.nysc_state_code_document);

    if (
      !hasStoredCallupVerification &&
      (!(verificationDraft.callup.document instanceof File) || verificationDraft.callup.document.size === 0)
    ) {
      throw new Error("Re-attach your NYSC call-up document before submitting.");
    }
    if (
      !hasStoredStateCodeVerification &&
      (!(verificationDraft.state_code.document instanceof File) || verificationDraft.state_code.document.size === 0)
    ) {
      throw new Error("Re-attach your NYSC state code document before submitting.");
    }

    if (!hasStoredBiodataVerification) {
      await apiFetch("/verification/attempts/", {
        method: "POST",
        body: JSON.stringify({
          verification_type: "biodata",
          first_name: verificationDraft.biodata.first_name,
          middle_name: verificationDraft.biodata.middle_name,
          surname: verificationDraft.biodata.surname,
          date_of_birth: verificationDraft.biodata.date_of_birth,
          gender: verificationDraft.biodata.gender,
          mobile_number: verificationDraft.biodata.mobile_number,
          state_of_origin: verificationDraft.biodata.state_of_origin,
          country_of_birth: verificationDraft.biodata.country_of_birth,
          university_matriculation_number: verificationDraft.biodata.university_matriculation_number,
        }),
      });
    }

    if (!hasStoredNinVerification) {
      await apiFetch("/verification/attempts/", {
        method: "POST",
        body: JSON.stringify({
          verification_type: "nin",
          submitted_value: verificationDraft.nin.submitted_value,
        }),
      });
    }

    if (!hasStoredCallupVerification && verificationDraft.callup.document instanceof File) {
      const callupFormData = new FormData();
      callupFormData.set("verification_type", "callup");
      callupFormData.set("submitted_value", verificationDraft.callup.submitted_value);
      callupFormData.set("document", verificationDraft.callup.document);
      await apiFetch("/verification/attempts/", {
        method: "POST",
        formData: true,
        body: callupFormData,
      });
    }

    if (!hasStoredStateCodeVerification && verificationDraft.state_code.document instanceof File) {
      const stateCodeFormData = new FormData();
      stateCodeFormData.set("verification_type", "state_code");
      stateCodeFormData.set("submitted_value", verificationDraft.state_code.submitted_value);
      stateCodeFormData.set("document", verificationDraft.state_code.document);
      await apiFetch("/verification/attempts/", {
        method: "POST",
        formData: true,
        body: stateCodeFormData,
      });
    }
  }

  async function submitTerms() {
    if (!allDocumentsChecked) {
      return;
    }

    setIsSubmitting(true);
    try {
      if (role === "corper" && !profile.data?.terms_accepted) {
        await submitCorperVerificationDraft();
      }

      const updatedProfile = await apiFetch<TermsProfile>(config.submitEndpoint, {
        method: "POST",
        body: JSON.stringify({
          accepted_terms_of_agreement: true,
          accepted_terms_of_use: true,
          accepted_documents: resolvedDocuments.map((document) => document.slug),
        }),
      });
      const successRedirect = resolveSuccessRedirect(role, updatedProfile);
      const profileCompleted =
        role === "corper"
          ? corperDocumentsAlreadyVerified(updatedProfile) && updatedProfile.is_complete
          : updatedProfile.is_complete;

      if (role === "corper") {
        clearDraft();
      }

      if (session) {
        updateSession({
          ...session,
          user: {
            ...session.user,
            profile_completed: profileCompleted,
            profile_path: successRedirect,
            company_verification_status:
              updatedProfile.verification_status ?? session.user.company_verification_status,
          },
        });
      }

      window.dispatchEvent(new Event("corper-profile-updated"));
      toast.success(config.submitMessage, { duration: 6000 });
      router.replace(successRedirect);
    } catch (error) {
      if (role === "corper") {
        toast.error(getLegalAgreementErrorMessage(error), { duration: 6000 });
        return;
      }
      toast.error(error instanceof Error ? error.message : "Unable to record agreement.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <DashboardShell role={role} title={config.title}>
      {!profile.data && profile.loading ? (
        <Card>
          <p className="text-sm text-mist">Loading legal documents...</p>
        </Card>
      ) : !profile.data ? (
        <Card>
          <p className="text-sm text-mist">{profile.error ?? "Unable to load your legal documents."}</p>
        </Card>
      ) : !canSubmitProfile ? (
        <Card className="grid gap-4">
          <p className="text-sm text-mist">
            {role === "company"
              ? "Complete the required company verification fields before you can accept and submit these legal documents."
              : "Return to the verification page to complete your verification details before submitting these legal documents."}
          </p>
          <div>
            <Button type="button" onClick={() => router.push(config.backHref)}>
              {role === "company" ? "Back to verification" : "Back to verification"}
            </Button>
          </div>
        </Card>
      ) : role === "corper" && !profile.data.terms_accepted && !hasVerificationDraft && !profile.data.full_name ? (
        <Card className="grid gap-4">
          <p className="text-sm text-mist">
            Return to the verification page, and complete all fields and upload the required NYSC documents before reviewing and submitting the legal agreements.
          </p>
          <div>
            <Button type="button" onClick={() => router.push(config.backHref)}>
              Back to verification
            </Button>
          </div>
        </Card>
      ) : profile.data.terms_accepted ? (
        <Card className="grid gap-4">
          <div className="grid gap-2">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Already accepted</p>
            <h2 className="font-display text-2xl text-white">Your legal agreements are on record</h2>
            <p className="text-sm text-mist">
              Signer: <span className="text-white">{signerName || "Not available"}</span>
              {" · "}
              Date: <span className="text-white">{agreementDate}</span>
            </p>
          </div>
          <div>
            <Button
              type="button"
              onClick={() => router.push(resolveSuccessRedirect(role, profile.data!))}
            >
              Continue
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-5">
          <Card className="grid gap-4">
            <div className="grid gap-2">
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Binding agreement</p>
              <h3 className="font-display text-xl text-white">{config.reviewTitle}</h3>
              <br />
              <div className="grid gap-1 text-sm text-mist">
                <p>
                  Signer: <span className="text-white">{signerName || "Not available"}</span>
                </p>
                <p>
                  Date: <span className="text-white">{agreementDate}</span>
                </p>
                {role === "corper" ? (
                  <>
                    <p>
                      NYSC State Code:{" "}
                      <span className="text-white">
                        {verificationDraft.state_code.submitted_value || profile.data.nysc_state_code || "Pending"}
                      </span>
                    </p>
                    <p>
                      NYSC Call-up Number:{" "}
                      <span className="text-white">
                        {verificationDraft.callup.submitted_value || profile.data.nysc_callup_number || "Pending"}
                      </span>
                    </p>
                  </>
                ) : null}
              </div>
            </div>
          </Card>

          {resolvedDocuments.map((document) => (
            <LegalDocumentAcceptanceCard
              key={document.slug}
              legalDocument={document}
              accepted={Boolean(acceptedDocuments[document.slug])}
              checked={Boolean(checkedDocuments[document.slug])}
              onCheckedChange={(checked) =>
                setCheckedDocuments((current) => ({
                  ...current,
                  [document.slug]: checked,
                }))
              }
            />
          ))}

          <div className="grid gap-3">
            <div className="flex items-center justify-between gap-3">
              <Button type="button" variant="secondary" onClick={() => router.push(config.backHref)}>
                Back
              </Button>
              <Button type="button" onClick={() => void submitTerms()} disabled={!allDocumentsChecked || isSubmitting}>
                {isSubmitting ? "Submitting..." : "Submit"}
              </Button>
            </div>
            <PpaDisclaimerNote />
          </div>
        </div>
      )}
    </DashboardShell>
  );
}
