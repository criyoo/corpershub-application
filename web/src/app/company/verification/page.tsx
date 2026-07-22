"use client";

import clsx from "clsx";
import { FileText, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/components/providers/auth-provider";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import {
  COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE,
  TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE,
  formatCompanyApprovalStatus,
  formatCompanyVerificationStatus,
  getCompanyApprovalTone,
  getCompanyVerificationTone,
  normalizeCompanyRegistrationNumber,
  validateCompanyRegistrationNumber,
  validateTaxIdentificationNumber,
} from "@/lib/company-verification";
import { NIGERIAN_STATES } from "@/lib/nigerian-reference-data";

type CompanyVerificationProfile = {
  id: string;
  company_name: string;
  company_registration_number: string;
  company_registration_date: string | null;
  company_location_state: string;
  tax_identification_number: string;
  verification_status: string;
  approval_status: string;
  verification_fields_complete: boolean;
  terms_accepted: boolean;
};

type CompanyVerificationFormValues = {
  company_name: string;
  company_registration_date: string;
  company_location_state: string;
  company_registration_number: string;
  tax_identification_number: string;
};

type CompanyVerificationFieldKey = keyof CompanyVerificationFormValues;

const EMPTY_FORM_VALUES: CompanyVerificationFormValues = {
  company_name: "",
  company_registration_date: "",
  company_location_state: "",
  company_registration_number: "",
  tax_identification_number: "",
};

const COMPANY_VERIFICATION_FORM_STORAGE_KEY = "corpershub.company-verification-form-values";
const PLACEHOLDER_CLASS_NAME = "placeholder:!text-sm placeholder:!text-[grey]";
const TEMPORARY_FIELD_ERROR_CLASS_NAME =
  "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50";
const PLACEHOLDER_OPTION_STYLE = {
  color: "grey",
  fontSize: "0.875rem",
} as const;

const REQUIRED_COMPANY_VERIFICATION_FIELDS: Array<{
  key: CompanyVerificationFieldKey;
  label: string;
}> = [
  { key: "company_name", label: "company name" },
  { key: "company_registration_date", label: "company registration date" },
  { key: "company_location_state", label: "state registered" },
  { key: "company_registration_number", label: "company registration number" },
  { key: "tax_identification_number", label: "tax identification number" },
];

function stringValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function loadFormValuesFromStorage(): CompanyVerificationFormValues | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const stored = window.sessionStorage.getItem(COMPANY_VERIFICATION_FORM_STORAGE_KEY);
    if (!stored) {
      return null;
    }
    const parsedValue = JSON.parse(stored) as unknown;
    if (!parsedValue || typeof parsedValue !== "object") {
      return null;
    }
    const parsed = parsedValue as Partial<Record<keyof CompanyVerificationFormValues, unknown>>;
    return {
      company_name: stringValue(parsed.company_name),
      company_registration_date: stringValue(parsed.company_registration_date),
      company_location_state: stringValue(parsed.company_location_state),
      company_registration_number: normalizeCompanyRegistrationNumber(
        stringValue(parsed.company_registration_number)
      ),
      tax_identification_number: stringValue(parsed.tax_identification_number),
    };
  } catch {
    return null;
  }
}

function saveFormValuesToStorage(values: CompanyVerificationFormValues) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.setItem(COMPANY_VERIFICATION_FORM_STORAGE_KEY, JSON.stringify(values));
  } catch {
    // Ignore storage errors so the form remains usable in private browsing modes.
  }
}

function clearFormValuesFromStorage() {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.sessionStorage.removeItem(COMPANY_VERIFICATION_FORM_STORAGE_KEY);
  } catch {
    // Ignore storage errors so successful submission is not blocked.
  }
}

function mapProfileToFormValues(profile: CompanyVerificationProfile): CompanyVerificationFormValues {
  return {
    company_name: profile.company_name ?? "",
    company_registration_date: profile.company_registration_date ?? "",
    company_location_state: profile.company_location_state.split(",")[0]?.trim() ?? "",
    company_registration_number: normalizeCompanyRegistrationNumber(
      profile.company_registration_number
    ),
    tax_identification_number: profile.tax_identification_number ?? "",
  };
}

function getMissingCompanyVerificationFields(formValues: CompanyVerificationFormValues) {
  return REQUIRED_COMPANY_VERIFICATION_FIELDS.filter((field) => !formValues[field.key].trim());
}

function FieldCard({
  icon: Icon,
  eyebrow,
  title,
  description,
}: {
  icon: typeof FileText;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <Card className="grid gap-3 bg-white/[0.03]">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/12 bg-white/[0.06]">
        <Icon className="h-5 w-5 text-lime" />
      </div>
      <div className="grid gap-1.5">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-lime">{eyebrow}</p>
        <h3 className="font-display text-xl text-white">{title}</h3>
        <p className="text-xs text-mist">{description}</p>
      </div>
    </Card>
  );
}

export default function CompanyVerificationPage() {
  const router = useRouter();
  const { hydrated, session, updateSession } = useAuth();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "company";
  const profile = useApiQuery<CompanyVerificationProfile>("/companies/me/verification/", protectedQueryEnabled);
  const [formValues, setFormValues] = useState<CompanyVerificationFormValues>(EMPTY_FORM_VALUES);
  const [isSaving, setIsSaving] = useState(false);
  const [highlightedFields, setHighlightedFields] = useState<Set<CompanyVerificationFieldKey>>(
    () => new Set()
  );
  const hasInitializedForm = useRef(false);
  const shouldPersistDraft = useRef(false);

  useEffect(() => {
    if (!profile.data || hasInitializedForm.current) {
      return;
    }
    const storedFormValues = loadFormValuesFromStorage();
    setFormValues(storedFormValues ?? mapProfileToFormValues(profile.data));
    shouldPersistDraft.current = Boolean(storedFormValues);
    hasInitializedForm.current = true;
  }, [profile.data]);

  useEffect(() => {
    if (!shouldPersistDraft.current) {
      return;
    }
    saveFormValuesToStorage(formValues);
  }, [formValues]);

  useEffect(() => {
    if (highlightedFields.size === 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setHighlightedFields(new Set());
    }, 3500);

    return () => window.clearTimeout(timeoutId);
  }, [highlightedFields]);

  function clearHighlightedField(field: CompanyVerificationFieldKey) {
    setHighlightedFields((current) => {
      if (!current.has(field)) {
        return current;
      }
      const nextFields = new Set(current);
      nextFields.delete(field);
      return nextFields;
    });
  }

  function isFieldHighlighted(field: CompanyVerificationFieldKey) {
    return highlightedFields.has(field);
  }

  function handleChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.target;
    clearHighlightedField(name as CompanyVerificationFieldKey);
    shouldPersistDraft.current = true;
    setFormValues((current) => ({
      ...current,
      [name]:
        name === "company_registration_number"
          ? normalizeCompanyRegistrationNumber(value)
          : value,
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const missingFields = getMissingCompanyVerificationFields(formValues);
    if (missingFields.length > 0) {
      setHighlightedFields(new Set(missingFields.map((field) => field.key)));
      toast.error(`Complete required company verification fields: ${missingFields.map((field) => field.label).join(", ")}.`);
      return;
    }

    const registrationNumberValidation = validateCompanyRegistrationNumber(
      formValues.company_registration_number
    );
    if (registrationNumberValidation.error) {
      setHighlightedFields(new Set(["company_registration_number"]));
      toast.error(registrationNumberValidation.error);
      return;
    }

    const taxIdentificationNumberValidation = validateTaxIdentificationNumber(
      formValues.tax_identification_number
    );
    if (taxIdentificationNumberValidation.error) {
      setHighlightedFields(new Set(["tax_identification_number"]));
      toast.error(taxIdentificationNumberValidation.error);
      return;
    }

    if (!formValues.company_name.trim()) {
      setHighlightedFields(new Set(["company_name"]));
      toast.error("Company name is required.");
      return;
    }

    setHighlightedFields(new Set());
    setIsSaving(true);
    try {
      const updatedProfile = await apiFetch<CompanyVerificationProfile>("/companies/me/verification/", {
        method: "PATCH",
        body: JSON.stringify({
          company_name: formValues.company_name.trim(),
          company_registration_date: formValues.company_registration_date.trim() || null,
          company_location_state: formValues.company_location_state.trim(),
          company_registration_number: registrationNumberValidation.normalizedValue,
          tax_identification_number: taxIdentificationNumberValidation.normalizedValue,
        }),
      });

      if (session) {
        updateSession({
          ...session,
          user: {
            ...session.user,
            company_verification_status: updatedProfile.verification_status,
            profile_path: updatedProfile.terms_accepted ? "/company/profile" : "/company/profile/terms",
          },
        });
      }

      toast.success(
        updatedProfile.terms_accepted
          ? "Company verification details updated."
          : "Company verification details saved."
      );
      shouldPersistDraft.current = false;
      clearFormValuesFromStorage();
      router.push(updatedProfile.terms_accepted ? "/company/profile" : "/company/profile/terms");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to save verification details.");
    } finally {
      setIsSaving(false);
    }
  }

  const verificationStatusLabel = formatCompanyVerificationStatus(profile.data?.verification_status);
  const verificationStatusTone = getCompanyVerificationTone(profile.data?.verification_status);
  const approvalStatusLabel = formatCompanyApprovalStatus(profile.data?.approval_status);
  const approvalStatusTone = getCompanyApprovalTone(profile.data?.approval_status);

  return (
    <DashboardShell role="company" title="Company verification">
      {!profile.data && profile.loading ? (
        <Card>
          <p className="text-sm text-mist">Loading company verification...</p>
        </Card>
      ) : !profile.data ? (
        <Card>
          <p className="text-sm text-mist">{profile.error ?? "Unable to load company verification."}</p>
        </Card>
      ) : (
        <div className="grid gap-6">
          <div className="grid gap-4 lg:grid-cols-3">
            <FieldCard
              icon={Sparkles}
              eyebrow="Company details"
              title="Provide company identity"
              description="Enter company registered details."
            />
            <FieldCard
              icon={ShieldCheck}
              eyebrow="CAC rules"
              title="Use CAC format"
              description="Registration numbers e.g RC7876483 or BN12345."
            />
            <FieldCard
              icon={FileText}
              eyebrow="Next step"
              title="Review legal documents"
              description="Save details, accept legal terms and complete your profile."
            />
          </div>

          <Card className="grid gap-5 bg-white/[0.02]">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="grid gap-2">
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Verification status</p>
                <h2 className="font-display text-2xl text-white">Verify your company details</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={verificationStatusTone}>{verificationStatusLabel}</Badge>
                <Badge tone={approvalStatusTone}>{approvalStatusLabel}</Badge>
              </div>
            </div>

            <form className="grid gap-5" onSubmit={handleSubmit} noValidate>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-1.5 text-sm text-mist md:col-span-2">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">Company Name</span>
                  <Input
                    name="company_name"
                    placeholder="Company name"
                    value={formValues.company_name}
                    onChange={handleChange}
                    required
                    hasError={isFieldHighlighted("company_name")}
                    className={clsx(PLACEHOLDER_CLASS_NAME, isFieldHighlighted("company_name") && TEMPORARY_FIELD_ERROR_CLASS_NAME)}
                  />
                </label>

                <label className="grid gap-1.5 text-sm text-mist">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">
                    Company Registration Date
                  </span>
                  <Input
                    name="company_registration_date"
                    type="date"
                    value={formValues.company_registration_date}
                    onChange={handleChange}
                    hasError={isFieldHighlighted("company_registration_date")}
                    className={clsx(
                      PLACEHOLDER_CLASS_NAME,
                      isFieldHighlighted("company_registration_date") && TEMPORARY_FIELD_ERROR_CLASS_NAME
                    )}
                  />
                </label>

                <label className="grid gap-1.5 text-sm text-mist">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">
                    State Registered
                  </span>
                  <Select
                    name="company_location_state"
                    value={formValues.company_location_state}
                    onChange={handleChange}
                    hasError={isFieldHighlighted("company_location_state")}
                    className={isFieldHighlighted("company_location_state") ? TEMPORARY_FIELD_ERROR_CLASS_NAME : undefined}
                    style={formValues.company_location_state ? undefined : PLACEHOLDER_OPTION_STYLE}
                  >
                    <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                      Select state
                    </option>
                    {NIGERIAN_STATES.map((state) => (
                      <option key={state} value={state}>
                        {state}
                      </option>
                    ))}
                  </Select>
                </label>

                <label className="grid gap-1.5 text-sm text-mist">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">
                    Company Registration Number
                  </span>
                  <Input
                    name="company_registration_number"
                    placeholder="e.g. RC7876483"
                    value={formValues.company_registration_number}
                    onChange={handleChange}
                    pattern="(?:RC|BN|IT|LP|LLP)[0-9]{5,10}"
                    title={COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE}
                    autoCapitalize="characters"
                    spellCheck={false}
                    maxLength={13}
                    required
                    hasError={isFieldHighlighted("company_registration_number")}
                    className={clsx(
                      PLACEHOLDER_CLASS_NAME,
                      isFieldHighlighted("company_registration_number") && TEMPORARY_FIELD_ERROR_CLASS_NAME
                    )}
                  />
                </label>

                <label className="grid gap-1.5 text-sm text-mist">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">
                    Tax Identification Number
                  </span>
                  <Input
                    name="tax_identification_number"
                    placeholder="Tax identification number"
                    value={formValues.tax_identification_number}
                    onChange={handleChange}
                    pattern="[0-9]{10,13}"
                    title={TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE}
                    inputMode="numeric"
                    spellCheck={false}
                    maxLength={13}
                    required
                    hasError={isFieldHighlighted("tax_identification_number")}
                    className={clsx(
                      PLACEHOLDER_CLASS_NAME,
                      isFieldHighlighted("tax_identification_number") && TEMPORARY_FIELD_ERROR_CLASS_NAME
                    )}
                  />
                </label>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5">
                <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs tracking-[0.12em] text-lime">
                  <ShieldCheck className="h-5 w-5text-lime" />
                  CAC registration numbers must be entered without spaces
                </div>
                <Button type="submit" disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save and continue"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}
