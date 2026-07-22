"use client";

import clsx from "clsx";
import { useRouter, useSearchParams } from "next/navigation";
import { Upload } from "lucide-react";
import {
  Suspense,
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { MultiSelectDropdown } from "@/components/ui/multi-select-dropdown";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { COMPANY_SECTOR_OPTIONS } from "@/lib/company-sectors";
import { toCourseOptionGroups, type CourseCatalogResponse } from "@/lib/course-catalog";
import { getCompanyMonogram } from "@/lib/company-directory";
import {
  COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE,
  TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE,
  formatCompanyVerificationStatus,
  getCompanyVerificationTone,
  normalizeCompanyRegistrationNumber,
  validateCompanyRegistrationNumber,
  validateTaxIdentificationNumber,
} from "@/lib/company-verification";
import { processCompanyProfileImage } from "@/lib/image-processing";
import { resolveMediaUrl } from "@/lib/media";
import {
  NIGERIAN_DEGREE_GROUPS,
  NIGERIAN_STATES,
} from "@/lib/nigerian-reference-data";
import { NIGERIAN_UNIVERSITY_GROUPS } from "@/lib/nigerian-universities";
import {
  normalizeNigerianMobileForDisplay,
  normalizeNigerianMobileInput,
  validateNigerianMobileNumber,
} from "@/lib/nigerian-validation";

type CompanyProfile = {
  id: string;
  company_name: string;
  company_registration_number: string;
  company_registration_date: string | null;
  tax_identification_number: string;
  company_image: string | null;
  company_location_state: string;
  preferred_deployment_states: string;
  company_location_city: string;
  company_address: string;
  head_office_address: string;
  company_website: string;
  company_sector: string;
  organization_type: string;
  staff_count_range: string;
  ppa_capacity: number | null;
  office_location_count: number | null;
  placement_type: string;
  monthly_allowance_offered: string;
  accommodation_provided: string;
  ppa_support: string;
  desired_corper_description: string;
  desired_qualification: string;
  desired_age_range: string;
  desired_field_of_study: string;
  desired_university: string;
  desired_posting_states: string;
  desired_skills: string;
  desired_experience: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  directors_name: string;
  director_phone_number: string;
  verification_status: string;
  approval_status: string;
  is_complete: boolean;
  profile_fields_complete: boolean;
  verification_fields_complete: boolean;
  terms_accepted: boolean;
};

type CompanyProfileFormValues = {
  company_name: string;
  company_registration_number: string;
  company_registration_date: string;
  tax_identification_number: string;
  company_location_state: string[];
  preferred_deployment_states: string[];
  company_location_city: string;
  company_address: string;
  head_office_address: string;
  company_website: string;
  company_sector: string;
  organization_type: string;
  organization_type_other: string;
  staff_count_range: string;
  ppa_capacity: string;
  office_location_count: string;
  placement_type: string[];
  monthly_allowance_offered: string;
  accommodation_provided: string;
  ppa_support: string;
  desired_corper_description: string;
  desired_qualification: string[];
  desired_age_range: string;
  desired_field_of_study: string[];
  desired_university: string[];
  desired_posting_states: string[];
  desired_skills: string;
  desired_experience: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  directors_name: string;
  director_phone_number: string;
};

type CompanyProfileFieldKey = keyof CompanyProfileFormValues | "company_image";

type CompanyProfilePayload = {
  company_name: string;
  company_registration_number: string;
  company_registration_date: string;
  tax_identification_number: string;
  company_location_state: string;
  preferred_deployment_states: string;
  company_location_city: string;
  company_address: string;
  head_office_address: string;
  company_website: string;
  company_sector: string;
  organization_type: string;
  staff_count_range: string;
  ppa_capacity: string;
  office_location_count: string;
  placement_type: string;
  monthly_allowance_offered: string;
  accommodation_provided: string;
  ppa_support: string;
  desired_corper_description: string;
  desired_qualification: string;
  desired_age_range: string;
  desired_field_of_study: string;
  desired_university: string;
  desired_posting_states: string;
  desired_skills: string;
  desired_experience: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  directors_name: string;
  director_phone_number: string;
};

const EMPTY_FORM_VALUES: CompanyProfileFormValues = {
  company_name: "",
  company_registration_number: "",
  company_registration_date: "",
  tax_identification_number: "",
  company_location_state: [],
  preferred_deployment_states: [],
  company_location_city: "",
  company_address: "",
  head_office_address: "",
  company_website: "",
  company_sector: "",
  organization_type: "",
  organization_type_other: "",
  staff_count_range: "",
  ppa_capacity: "",
  office_location_count: "",
  placement_type: [],
  monthly_allowance_offered: "",
  accommodation_provided: "",
  ppa_support: "",
  desired_corper_description: "",
  desired_qualification: [],
  desired_age_range: "",
  desired_field_of_study: [],
  desired_university: [],
  desired_posting_states: [],
  desired_skills: "",
  desired_experience: "",
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  directors_name: "",
  director_phone_number: "",
};

const ANY_QUALIFICATION_OPTION = "Any Qualification";
const ANY_FIELD_OF_STUDY_OPTION = "Any Field of Study";
const ANY_UNIVERSITY_OPTION = "Any University";
const QUALIFICATION_OPTIONS = [
  {
    label: "Preference",
    options: [ANY_QUALIFICATION_OPTION],
  },
  ...NIGERIAN_DEGREE_GROUPS.map((group) => ({
    label: group.label,
    options: group.degrees,
  })),
];
const STATE_OF_OPERATION_OPTIONS = [
  {
    label: "States in Nigeria",
    options: NIGERIAN_STATES,
  },
];
const DESIRED_UNIVERSITY_OPTIONS = [
  {
    label: "Preference",
    options: [ANY_UNIVERSITY_OPTION],
  },
  ...NIGERIAN_UNIVERSITY_GROUPS.map((group) => ({
    label: group.label,
    options: group.universities,
  })),
];
const STAFF_COUNT_RANGE_OPTIONS = [
  "1-10",
  "11-50",
  "51-200",
  "200-1000",
  "Above 1000",
];
const PLACEMENT_TYPE_OPTIONS = [
  "Full-time / On-Site",
  "Full-time / Remote",
  "Full-time / Hybrid",
  "Part-Time / On-Site",
  "Part-Time / Remote",
  "Part-Time / Hybrid",
];
const MONTHLY_ALLOWANCE_OPTIONS = [
  "None",
  "Below N25,000",
  "N25,000-N50,000",
  "N50,000-N100,000",
  "Above N100,000",
  "Negotiable",
];
const ACCOMMODATION_OPTIONS = ["Yes", "No", "Willing to discuss"];
const PPA_SUPPORT_OPTIONS = ["Yes", "No", "Willing to discuss"];
const PLACEMENT_TYPE_OPTION_GROUPS = [
  {
    label: "Placement options",
    options: PLACEMENT_TYPE_OPTIONS,
  },
];
const ORGANIZATION_TYPE_OPTIONS = [
  "Business Name (Sole Proprietorship)",
  "Company Limited by Guarantee (Ltd/Gte)",
  "Incorporated Trustee (IT)",
  "Limited Liability Partnership (LLP)",
  "Limited Partnership (LP)",
  "Private Company Limited by Shares (Ltd)",
  "Public Company Limited by Shares (PLC)",
  "Unlimited Company (Ultd)",
];
const CUSTOM_ORGANIZATION_TYPE_OPTION = "Others";


const GENERAL_LABEL = "grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45";
const GENERAL_DIV = "grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45";
const PLACEHOLDER_CLASS_NAME = "placeholder:!text-sm placeholder:!text-gray-400";
const TEMPORARY_FIELD_ERROR_CLASS_NAME =
  "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50";
const EMPTY_SELECT_CLASS_NAME = "!text-sm !text-gray-400";
const EMPTY_DROPDOWN_SUMMARY_CLASS_NAME = "!text-sm !text-gray-400";
const CHECKBOX_CLASS_NAME = "h-4 w-4 rounded border-white/20 bg-transparent accent-[#1FB766]";
const PLACEHOLDER_OPTION_STYLE: CSSProperties = {
  color: "#9CA3AF",
  fontSize: "0.875rem",
};

function selectClassName(value: string) {
  return value ? undefined : EMPTY_SELECT_CLASS_NAME;
}

function selectPlaceholderStyle(value: string) {
  return value ? undefined : PLACEHOLDER_OPTION_STYLE;
}

function dropdownSummaryClassName(values: string[]) {
  return values.length > 0 ? undefined : EMPTY_DROPDOWN_SUMMARY_CLASS_NAME;
}

function fieldLabel(label: string, required = false) {
  return required ? `${label} *` : label;
}

function parseCommaSeparatedValues(value: string | null | undefined) {
  return Array.from(
    new Set(
      (value ?? "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
}

function parseQualificationValues(value: string | null | undefined) {
  return Array.from(
    new Set(
      (value ?? "")
        .replace(/\s*\/\s*/g, ",")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
}

function serializeMultiSelectValues(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean))).join(", ");
}

function normalizeExclusiveSelection(values: string[], exclusiveOption: string) {
  const normalizedValues = Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
  if (!normalizedValues.includes(exclusiveOption)) {
    return normalizedValues;
  }
  return [exclusiveOption];
}

function serializeExclusiveMultiSelectValues(values: string[], exclusiveOption: string) {
  return serializeMultiSelectValues(normalizeExclusiveSelection(values, exclusiveOption));
}

function shouldSyncTextValues(sourceValue: string, targetValue: string) {
  const normalizedSourceValue = sourceValue.trim();
  const normalizedTargetValue = targetValue.trim();
  return Boolean(
    normalizedSourceValue &&
    normalizedTargetValue &&
    normalizedSourceValue === normalizedTargetValue
  );
}

function shouldSyncListValues(sourceValues: string[], targetValues: string[]) {
  if (sourceValues.length === 0 || targetValues.length === 0) {
    return false;
  }
  const normalizeValues = (values: string[]) =>
    values.map((value) => value.trim()).filter(Boolean).sort();
  const normalizedSourceValues = normalizeValues(sourceValues);
  const normalizedTargetValues = normalizeValues(targetValues);
  return (
    normalizedSourceValues.length === normalizedTargetValues.length &&
    normalizedSourceValues.every((value, index) => value === normalizedTargetValues[index])
  );
}

function splitOrganizationType(value: string | null | undefined) {
  const normalizedValue = (value ?? "").trim();
  if (!normalizedValue) {
    return {
      organizationType: "",
      organizationTypeOther: "",
    };
  }

  if (ORGANIZATION_TYPE_OPTIONS.includes(normalizedValue)) {
    return {
      organizationType: normalizedValue,
      organizationTypeOther: "",
    };
  }

  return {
    organizationType: CUSTOM_ORGANIZATION_TYPE_OPTION,
    organizationTypeOther: normalizedValue,
  };
}

function splitCompanySector(value: string | null | undefined) {
  const normalizedValue = (value ?? "").trim();
  return {
    companySector: COMPANY_SECTOR_OPTIONS.includes(normalizedValue) ? normalizedValue : "",
    companySectorOther: "",
  };
}

function mapProfileToForm(profile: CompanyProfile): CompanyProfileFormValues {
  const { companySector } = splitCompanySector(profile.company_sector);
  const { organizationType, organizationTypeOther } = splitOrganizationType(
    profile.organization_type
  );
  return {
    company_name: profile.company_name ?? "",
    company_registration_number: normalizeCompanyRegistrationNumber(
      profile.company_registration_number
    ),
    company_registration_date: profile.company_registration_date ?? "",
    tax_identification_number: profile.tax_identification_number ?? "",
    company_location_state: parseCommaSeparatedValues(profile.company_location_state),
    preferred_deployment_states: parseCommaSeparatedValues(profile.preferred_deployment_states),
    company_location_city: profile.company_location_city ?? "",
    company_address: profile.company_address ?? "",
    head_office_address: profile.head_office_address ?? "",
    company_website: profile.company_website ?? "",
    company_sector: companySector,
    organization_type: organizationType,
    organization_type_other: organizationTypeOther,
    staff_count_range: profile.staff_count_range ?? "",
    ppa_capacity: profile.ppa_capacity ? String(profile.ppa_capacity) : "",
    office_location_count: profile.office_location_count
      ? String(profile.office_location_count)
      : "",
    placement_type: parseCommaSeparatedValues(profile.placement_type),
    monthly_allowance_offered: profile.monthly_allowance_offered ?? "",
    accommodation_provided: profile.accommodation_provided ?? "",
    ppa_support: profile.ppa_support ?? "",
    desired_corper_description: profile.desired_corper_description ?? "",
    desired_qualification: normalizeExclusiveSelection(
      parseQualificationValues(profile.desired_qualification),
      ANY_QUALIFICATION_OPTION
    ),
    desired_age_range: profile.desired_age_range ?? "",
    desired_field_of_study: normalizeExclusiveSelection(
      parseCommaSeparatedValues(profile.desired_field_of_study),
      ANY_FIELD_OF_STUDY_OPTION
    ),
    desired_university: normalizeExclusiveSelection(
      parseCommaSeparatedValues(profile.desired_university),
      ANY_UNIVERSITY_OPTION
    ),
    desired_posting_states: parseCommaSeparatedValues(profile.desired_posting_states),
    desired_skills: profile.desired_skills ?? "",
    desired_experience: profile.desired_experience ?? "",
    contact_name: profile.contact_name ?? "",
    contact_email: profile.contact_email ?? "",
    contact_phone: normalizeNigerianMobileForDisplay(profile.contact_phone ?? ""),
    directors_name: profile.directors_name ?? "",
    director_phone_number: normalizeNigerianMobileForDisplay(profile.director_phone_number ?? ""),
  };
}

function mergeStoredProfileDraftWithVerificationValues(
  storedValues: CompanyProfileFormValues,
  profileValues: CompanyProfileFormValues
): CompanyProfileFormValues {
  return {
    ...storedValues,
    company_name: profileValues.company_name || storedValues.company_name,
    company_registration_number:
      profileValues.company_registration_number || storedValues.company_registration_number,
    company_registration_date:
      profileValues.company_registration_date || storedValues.company_registration_date,
    tax_identification_number:
      profileValues.tax_identification_number || storedValues.tax_identification_number,
  };
}

function buildProfilePayload(formValues: CompanyProfileFormValues): CompanyProfilePayload {
  const organizationType =
    formValues.organization_type === CUSTOM_ORGANIZATION_TYPE_OPTION
      ? formValues.organization_type_other.trim()
      : formValues.organization_type.trim();

  return {
    company_name: formValues.company_name.trim(),
    company_registration_number: normalizeCompanyRegistrationNumber(
      formValues.company_registration_number
    ),
    company_registration_date: formValues.company_registration_date.trim(),
    tax_identification_number: formValues.tax_identification_number.trim(),
    company_location_state: serializeMultiSelectValues(formValues.company_location_state),
    preferred_deployment_states: serializeMultiSelectValues(formValues.preferred_deployment_states),
    company_location_city: formValues.company_location_city.trim(),
    company_address: formValues.company_address.trim(),
    head_office_address: formValues.head_office_address.trim(),
    company_website: formValues.company_website.trim(),
    company_sector: formValues.company_sector.trim(),
    organization_type: organizationType,
    staff_count_range: formValues.staff_count_range.trim(),
    ppa_capacity: formValues.ppa_capacity.trim(),
    office_location_count: formValues.office_location_count.trim(),
    placement_type: serializeMultiSelectValues(formValues.placement_type),
    monthly_allowance_offered: formValues.monthly_allowance_offered.trim(),
    accommodation_provided: formValues.accommodation_provided.trim(),
    ppa_support: formValues.ppa_support.trim(),
    desired_corper_description: formValues.desired_corper_description.trim(),
    desired_qualification: serializeExclusiveMultiSelectValues(
      formValues.desired_qualification,
      ANY_QUALIFICATION_OPTION
    ),
    desired_age_range: formValues.desired_age_range.trim(),
    desired_field_of_study: serializeExclusiveMultiSelectValues(
      formValues.desired_field_of_study,
      ANY_FIELD_OF_STUDY_OPTION
    ),
    desired_university: serializeExclusiveMultiSelectValues(
      formValues.desired_university,
      ANY_UNIVERSITY_OPTION
    ),
    desired_posting_states: serializeMultiSelectValues(formValues.desired_posting_states),
    desired_skills: formValues.desired_skills.trim(),
    desired_experience: formValues.desired_experience.trim(),
    contact_name: formValues.contact_name.trim(),
    contact_email: formValues.contact_email.trim(),
    contact_phone: formValues.contact_phone.trim(),
    directors_name: formValues.directors_name.trim(),
    director_phone_number: formValues.director_phone_number.trim(),
  };
}

function getMissingProfileFields(
  formValues: CompanyProfileFormValues,
  hasCompanyImage: boolean
) {
  const missingFields: Array<{ key: CompanyProfileFieldKey; label: string }> = [];

  if (!formValues.company_name.trim()) {
    missingFields.push({ key: "company_name", label: "company name" });
  }
  if (!formValues.company_registration_number.trim()) {
    missingFields.push({ key: "company_registration_number", label: "company registration number" });
  }
  if (!formValues.tax_identification_number.trim()) {
    missingFields.push({ key: "tax_identification_number", label: "tax identification number" });
  }
  if (!formValues.company_sector.trim()) {
    missingFields.push({ key: "company_sector", label: "company sector" });
  }
  if (!formValues.organization_type.trim()) {
    missingFields.push({ key: "organization_type", label: "organisation type" });
  }
  if (
    formValues.organization_type === CUSTOM_ORGANIZATION_TYPE_OPTION &&
    !formValues.organization_type_other.trim()
  ) {
    missingFields.push({ key: "organization_type_other", label: "organisation type" });
  }
  if (!formValues.staff_count_range.trim()) {
    missingFields.push({ key: "staff_count_range", label: "number of staff" });
  }
  if (!formValues.ppa_capacity.trim()) {
    missingFields.push({ key: "ppa_capacity", label: "PPA capacity" });
  }
  if (!formValues.office_location_count.trim()) {
    missingFields.push({ key: "office_location_count", label: "number of office locations" });
  }
  if (formValues.company_location_state.length === 0) {
    missingFields.push({ key: "company_location_state", label: "state(s) of operation" });
  }
  if (formValues.preferred_deployment_states.length === 0) {
    missingFields.push({ key: "preferred_deployment_states", label: "preferred states of deployment" });
  }
  if (!formValues.company_location_city.trim()) {
    missingFields.push({ key: "company_location_city", label: "city" });
  }
  if (!formValues.head_office_address.trim()) {
    missingFields.push({ key: "head_office_address", label: "head office address" });
  }
  if (!formValues.company_address.trim()) {
    missingFields.push({ key: "company_address", label: "company operating address" });
  }
  if (formValues.placement_type.length === 0) {
    missingFields.push({ key: "placement_type", label: "placement type" });
  }
  if (!formValues.monthly_allowance_offered.trim()) {
    missingFields.push({ key: "monthly_allowance_offered", label: "monthly allowance offered" });
  }
  if (!formValues.accommodation_provided.trim()) {
    missingFields.push({ key: "accommodation_provided", label: "accommodation provided" });
  }
  if (!formValues.directors_name.trim()) {
    missingFields.push({ key: "directors_name", label: "director's fullname" });
  }
  if (!formValues.director_phone_number.trim()) {
    missingFields.push({ key: "director_phone_number", label: "director's phone number" });
  }
  if (!formValues.contact_phone.trim()) {
    missingFields.push({ key: "contact_phone", label: "contact number" });
  }
  if (!formValues.contact_name.trim()) {
    missingFields.push({ key: "contact_name", label: "contact fullname" });
  }
  if (!formValues.contact_email.trim()) {
    missingFields.push({ key: "contact_email", label: "contact email" });
  }
  if (!formValues.desired_corper_description.trim()) {
    missingFields.push({ key: "desired_corper_description", label: "company summary" });
  }
  if (formValues.desired_qualification.length === 0) {
    missingFields.push({ key: "desired_qualification", label: "desired qualification" });
  }
  if (!formValues.desired_age_range.trim()) {
    missingFields.push({ key: "desired_age_range", label: "desired age range" });
  }
  if (formValues.desired_field_of_study.length === 0) {
    missingFields.push({ key: "desired_field_of_study", label: "desired field of study" });
  }
  if (formValues.desired_university.length === 0) {
    missingFields.push({ key: "desired_university", label: "desired university" });
  }
  if (formValues.desired_posting_states.length === 0) {
    missingFields.push({ key: "desired_posting_states", label: "desired posting state" });
  }
  if (!formValues.desired_skills.trim()) {
    missingFields.push({ key: "desired_skills", label: "desired skills" });
  }
  if (!formValues.desired_experience.trim()) {
    missingFields.push({ key: "desired_experience", label: "desired experience" });
  }
  if (!hasCompanyImage) {
    missingFields.push({ key: "company_image", label: "company image" });
  }

  return missingFields;
}

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function isValidHttpUrl(value: string) {
  try {
    const parsedUrl = new URL(value);
    return parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:";
  } catch {
    return false;
  }
}

function getInvalidProfileFields(formValues: CompanyProfileFormValues) {
  const invalidFields: Array<{ key: CompanyProfileFieldKey; label: string; message: string }> = [];
  const registrationNumberValidation = validateCompanyRegistrationNumber(
    formValues.company_registration_number
  );
  const taxIdentificationNumberValidation = validateTaxIdentificationNumber(
    formValues.tax_identification_number
  );
  const phoneValidation = validateNigerianMobileNumber(
    formValues.contact_phone,
    "Contact phone number",
    true,
    true
  );
  const directorPhoneValidation = validateNigerianMobileNumber(
    formValues.director_phone_number,
    "Director phone number",
    false,
    true
  );

  if (formValues.company_registration_number.trim() && registrationNumberValidation.error) {
    invalidFields.push({
      key: "company_registration_number",
      label: "company registration number",
      message: registrationNumberValidation.error,
    });
  }
  if (formValues.tax_identification_number.trim() && taxIdentificationNumberValidation.error) {
    invalidFields.push({
      key: "tax_identification_number",
      label: "tax identification number",
      message: taxIdentificationNumberValidation.error,
    });
  }
  if (formValues.contact_phone.trim() && phoneValidation.error) {
    invalidFields.push({
      key: "contact_phone",
      label: "contact number",
      message: phoneValidation.error,
    });
  }
  if (formValues.director_phone_number.trim() && directorPhoneValidation.error) {
    invalidFields.push({
      key: "director_phone_number",
      label: "director phone number",
      message: directorPhoneValidation.error,
    });
  }
  if (formValues.contact_email.trim() && !isValidEmail(formValues.contact_email)) {
    invalidFields.push({
      key: "contact_email",
      label: "contact email",
      message: "Enter a valid contact email.",
    });
  }
  if (formValues.company_website.trim() && !isValidHttpUrl(formValues.company_website)) {
    invalidFields.push({
      key: "company_website",
      label: "company website",
      message: "Enter a valid company website URL.",
    });
  }
  if (!/^\d+$/.test(formValues.ppa_capacity.trim()) || Number(formValues.ppa_capacity) < 1) {
    invalidFields.push({
      key: "ppa_capacity",
      label: "PPA capacity",
      message: "PPA capacity must be at least 1.",
    });
  }
  if (
    formValues.office_location_count.trim() &&
    (
      !/^\d+$/.test(formValues.office_location_count.trim()) ||
      Number(formValues.office_location_count) < 1
    )
  ) {
    invalidFields.push({
      key: "office_location_count",
      label: "number of office locations",
      message: "Number of office locations must be at least 1.",
    });
  }

  return invalidFields;
}

export default function CompanyProfilePage() {
  return (
    <Suspense fallback={null}>
      <CompanyProfilePageContent />
    </Suspense>
  );
}

const COMPANY_PROFILE_FORM_STORAGE_KEY = "company_profile_form_values";

function loadFormValuesFromStorage(): CompanyProfileFormValues | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.sessionStorage.getItem(COMPANY_PROFILE_FORM_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as CompanyProfileFormValues;
    }
  } catch {
    // ignore storage errors
  }
  return null;
}

function saveFormValuesToStorage(values: CompanyProfileFormValues) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.sessionStorage.setItem(COMPANY_PROFILE_FORM_STORAGE_KEY, JSON.stringify(values));
  } catch {
    // ignore storage errors
  }
}

function clearFormValuesFromStorage() {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.sessionStorage.removeItem(COMPANY_PROFILE_FORM_STORAGE_KEY);
  } catch {
    // ignore storage errors
  }
}

function CompanyProfilePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hydrated, session, updateSession } = useAuth();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "company";
  const { data, refetch, loading } = useApiQuery<CompanyProfile>("/companies/me/", protectedQueryEnabled);
  const { data: courseCatalog } = useApiQuery<CourseCatalogResponse>("/common/course-catalog/");
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [formValues, setFormValues] = useState<CompanyProfileFormValues>(EMPTY_FORM_VALUES);
  const [selectedCompanyImage, setSelectedCompanyImage] = useState<File | null>(null);
  const [companyImagePreviewUrl, setCompanyImagePreviewUrl] = useState<string | null>(null);
  const [isProcessingCompanyImage, setIsProcessingCompanyImage] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isCompanyAddressSameAsHeadOffice, setIsCompanyAddressSameAsHeadOffice] = useState(false);
  const [isContactNameSameAsDirector, setIsContactNameSameAsDirector] = useState(false);
  const [isContactPhoneSameAsDirector, setIsContactPhoneSameAsDirector] = useState(false);
  const [isDesiredPostingStateSameAsPreferred, setIsDesiredPostingStateSameAsPreferred] =
    useState(false);
  const [highlightedFields, setHighlightedFields] = useState<Set<CompanyProfileFieldKey>>(
    () => new Set()
  );
  const companyImageInputRef = useRef<HTMLInputElement>(null);
  const hasInitializedForm = useRef(false);
  const shouldPersistDraft = useRef(false);

  useEffect(() => {
    if (!data) {
      return;
    }
    const mappedProfileValues = mapProfileToForm(data);
    setProfile(data);

    let nextFormValues: CompanyProfileFormValues | null = null;
    if (!hasInitializedForm.current) {
      const stored = loadFormValuesFromStorage();
      nextFormValues = stored
        ? mergeStoredProfileDraftWithVerificationValues(stored, mappedProfileValues)
        : mappedProfileValues;
      shouldPersistDraft.current = Boolean(stored);
      hasInitializedForm.current = true;
    } else if (!shouldPersistDraft.current) {
      nextFormValues = mappedProfileValues;
    }

    if (nextFormValues) {
      setFormValues(nextFormValues);
      setIsCompanyAddressSameAsHeadOffice(
        shouldSyncTextValues(nextFormValues.head_office_address, nextFormValues.company_address)
      );
      setIsContactNameSameAsDirector(
        shouldSyncTextValues(nextFormValues.directors_name, nextFormValues.contact_name)
      );
      setIsContactPhoneSameAsDirector(
        shouldSyncTextValues(nextFormValues.director_phone_number, nextFormValues.contact_phone)
      );
      setIsDesiredPostingStateSameAsPreferred(
        shouldSyncListValues(
          nextFormValues.preferred_deployment_states,
          nextFormValues.desired_posting_states
        )
      );
    }
  }, [data]);

  useEffect(() => {
    if (!shouldPersistDraft.current) {
      return;
    }
    saveFormValuesToStorage(formValues);
  }, [formValues]);

  useEffect(() => {
    return () => {
      if (companyImagePreviewUrl) {
        URL.revokeObjectURL(companyImagePreviewUrl);
      }
    };
  }, [companyImagePreviewUrl]);

  useEffect(() => {
    if (highlightedFields.size === 0) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setHighlightedFields(new Set());
    }, 3500);

    return () => window.clearTimeout(timeoutId);
  }, [highlightedFields]);

  const isComplete = profile?.is_complete === true;
  const isEditMode = searchParams.get("edit") === "1";

  const canEditProfile = !isComplete || isEditMode;
  const canEditPhoto = canEditProfile;
  const verificationStatusLabel = formatCompanyVerificationStatus(profile?.verification_status);
  const verificationStatusTone = getCompanyVerificationTone(profile?.verification_status);
  const resolvedCompanyImageUrl = companyImagePreviewUrl || resolveMediaUrl(profile?.company_image);
  const companyDisplayName = formValues.company_name || profile?.company_name || "Company";
  const fieldOfStudyOptions = [
    {
      label: "Preference",
      options: [ANY_FIELD_OF_STUDY_OPTION],
    },
    ...toCourseOptionGroups(
      courseCatalog?.fields ?? [],
      formValues.desired_field_of_study.filter(
        (value) => value !== ANY_FIELD_OF_STUDY_OPTION
      )
    ),
  ];

  function isProfileFieldHighlighted(field: CompanyProfileFieldKey) {
    return highlightedFields.has(field);
  }

  function clearHighlightedField(field: CompanyProfileFieldKey) {
    setHighlightedFields((current) => {
      if (!current.has(field)) {
        return current;
      }
      const nextFields = new Set(current);
      nextFields.delete(field);
      return nextFields;
    });
  }

  function updateFormValue<Key extends keyof CompanyProfileFormValues>(
    name: Key,
    value: CompanyProfileFormValues[Key]
  ) {
    clearHighlightedField(name);
    shouldPersistDraft.current = true;
    setFormValues((current) => ({
      ...current,
      [name]: value,
    }));
  }

  function handleFieldChange(
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = event.target;
    clearHighlightedField(name as CompanyProfileFieldKey);
    const normalizedValue =
      name === "contact_phone" || name === "director_phone_number"
        ? normalizeNigerianMobileInput(value)
        : name === "company_registration_number"
          ? normalizeCompanyRegistrationNumber(value)
          : value;

    shouldPersistDraft.current = true;
    setFormValues((current) => ({
      ...current,
      [name]: normalizedValue,
      ...(name === "head_office_address" && isCompanyAddressSameAsHeadOffice
        ? { company_address: normalizedValue }
        : {}),
      ...(name === "directors_name" && isContactNameSameAsDirector
        ? { contact_name: normalizedValue }
        : {}),
      ...(name === "director_phone_number" && isContactPhoneSameAsDirector
        ? { contact_phone: normalizedValue }
        : {}),
      ...(name === "organization_type" && normalizedValue !== CUSTOM_ORGANIZATION_TYPE_OPTION
        ? { organization_type_other: "" }
        : {}),
    }));
  }

  function handleCompanyAddressSyncChange(event: ChangeEvent<HTMLInputElement>) {
    const { checked } = event.target;
    setIsCompanyAddressSameAsHeadOffice(checked);
    if (checked) {
      clearHighlightedField("company_address");
      updateFormValue("company_address", formValues.head_office_address);
    }
  }

  function handleContactNameSyncChange(event: ChangeEvent<HTMLInputElement>) {
    const { checked } = event.target;
    setIsContactNameSameAsDirector(checked);
    if (checked) {
      clearHighlightedField("contact_name");
      updateFormValue("contact_name", formValues.directors_name);
    }
  }

  function handleContactPhoneSyncChange(event: ChangeEvent<HTMLInputElement>) {
    const { checked } = event.target;
    setIsContactPhoneSameAsDirector(checked);
    if (checked) {
      clearHighlightedField("contact_phone");
      updateFormValue("contact_phone", formValues.director_phone_number);
    }
  }

  function handlePreferredDeploymentStatesChange(values: string[]) {
    clearHighlightedField("preferred_deployment_states");
    if (isDesiredPostingStateSameAsPreferred) {
      clearHighlightedField("desired_posting_states");
    }
    shouldPersistDraft.current = true;
    setFormValues((current) => ({
      ...current,
      preferred_deployment_states: values,
      ...(isDesiredPostingStateSameAsPreferred ? { desired_posting_states: values } : {}),
    }));
  }

  function handleDesiredPostingStateSyncChange(event: ChangeEvent<HTMLInputElement>) {
    const { checked } = event.target;
    setIsDesiredPostingStateSameAsPreferred(checked);
    if (checked) {
      clearHighlightedField("desired_posting_states");
      updateFormValue("desired_posting_states", formValues.preferred_deployment_states);
    }
  }

  function handleCompanyRegistrationNumberBlur() {
    if (!canEditProfile) {
      return;
    }

    if (!formValues.company_registration_number.trim()) {
      return;
    }
    updateFormValue(
      "company_registration_number",
      normalizeCompanyRegistrationNumber(formValues.company_registration_number)
    );
  }

  async function handleCompanyImageChange(event: ChangeEvent<HTMLInputElement>) {
    if (!canEditPhoto) {
      return;
    }

    const file = event.target.files?.[0] ?? null;
    clearHighlightedField("company_image");
    if (companyImagePreviewUrl) {
      URL.revokeObjectURL(companyImagePreviewUrl);
    }

    if (!file) {
      setSelectedCompanyImage(null);
      setCompanyImagePreviewUrl(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setSelectedCompanyImage(null);
      setCompanyImagePreviewUrl(null);
      setHighlightedFields(new Set(["company_image"]));
      if (companyImageInputRef.current) {
        companyImageInputRef.current.value = "";
      }
      toast.error("Company image must be smaller than 10MB.");
      return;
    }

    setIsProcessingCompanyImage(true);
    try {
      const processedFile = await processCompanyProfileImage(file);
      setSelectedCompanyImage(processedFile);
      setCompanyImagePreviewUrl(URL.createObjectURL(processedFile));
    } catch (error) {
      setSelectedCompanyImage(null);
      setCompanyImagePreviewUrl(null);
      setHighlightedFields(new Set(["company_image"]));
      if (companyImageInputRef.current) {
        companyImageInputRef.current.value = "";
      }
      toast.error(error instanceof Error ? error.message : "Unable to process the selected image.");
    } finally {
      setIsProcessingCompanyImage(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile || !canEditProfile) {
      return;
    }

    const missingFields = getMissingProfileFields(
      formValues,
      Boolean(selectedCompanyImage || profile.company_image)
    );
    if (missingFields.length > 0) {
      setHighlightedFields(new Set(missingFields.map((field) => field.key)));
      toast.error(
        `Complete all company profile fields before saving: ${missingFields.map((field) => field.label).join(", ")}.`
      );
      return;
    }

    const invalidFields = getInvalidProfileFields(formValues);
    if (invalidFields.length > 0) {
      setHighlightedFields(new Set(invalidFields.map((field) => field.key)));
      toast.error(invalidFields[0].message);
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

    const phoneValidation = validateNigerianMobileNumber(
      formValues.contact_phone,
      "Contact phone number",
      true,
      true
    );
    if (phoneValidation.error) {
      setHighlightedFields(new Set(["contact_phone"]));
      toast.error(phoneValidation.error);
      return;
    }

    const directorPhoneValidation = validateNigerianMobileNumber(
      formValues.director_phone_number,
      "Director phone number",
      false,
      true
    );
    if (directorPhoneValidation.error) {
      setHighlightedFields(new Set(["director_phone_number"]));
      toast.error(directorPhoneValidation.error);
      return;
    }

    if (!/^\d+$/.test(formValues.ppa_capacity.trim()) || Number(formValues.ppa_capacity) < 1) {
      setHighlightedFields(new Set(["ppa_capacity"]));
      toast.error("PPA capacity must be at least 1.");
      return;
    }

    if (
      formValues.office_location_count.trim() &&
      (
        !/^\d+$/.test(formValues.office_location_count.trim()) ||
        Number(formValues.office_location_count) < 1
      )
    ) {
      setHighlightedFields(new Set(["office_location_count"]));
      toast.error("Number of office locations must be at least 1.");
      return;
    }

    if (
      formValues.organization_type === CUSTOM_ORGANIZATION_TYPE_OPTION &&
      !formValues.organization_type_other.trim()
    ) {
      setHighlightedFields(new Set(["organization_type_other"]));
      toast.error("Enter the organisation type.");
      return;
    }

    setHighlightedFields(new Set());
    setIsSaving(true);
    try {
      const formData = new FormData();
      const payload = buildProfilePayload({
        ...formValues,
        company_registration_number: registrationNumberValidation.normalizedValue,
      });
      const updatePath = isEditMode ? "/companies/me/?edit=1" : "/companies/me/";
      Object.entries(payload).forEach(([key, value]) => {
        formData.set(
          key,
          key === "contact_phone"
            ? phoneValidation.normalizedValue
            : key === "director_phone_number"
              ? directorPhoneValidation.normalizedValue
              : key === "tax_identification_number"
                ? taxIdentificationNumberValidation.normalizedValue
                : value
        );
      });

      if (selectedCompanyImage) {
        formData.set("company_image", selectedCompanyImage);
      }

      const updatedProfile = await apiFetch<CompanyProfile>(updatePath, {
        method: "PATCH",
        formData: true,
        body: formData,
      });

      shouldPersistDraft.current = false;
      clearFormValuesFromStorage();
      setProfile(updatedProfile);
      const updatedFormValues = mapProfileToForm(updatedProfile);
      setFormValues(updatedFormValues);
      setIsCompanyAddressSameAsHeadOffice(
        shouldSyncTextValues(
          updatedFormValues.head_office_address,
          updatedFormValues.company_address
        )
      );
      setIsContactNameSameAsDirector(
        shouldSyncTextValues(updatedFormValues.directors_name, updatedFormValues.contact_name)
      );
      setIsContactPhoneSameAsDirector(
        shouldSyncTextValues(updatedFormValues.director_phone_number, updatedFormValues.contact_phone)
      );
      setIsDesiredPostingStateSameAsPreferred(
        shouldSyncListValues(
          updatedFormValues.preferred_deployment_states,
          updatedFormValues.desired_posting_states
        )
      );
      setSelectedCompanyImage(null);
      if (companyImageInputRef.current) {
        companyImageInputRef.current.value = "";
      }
      if (companyImagePreviewUrl) {
        URL.revokeObjectURL(companyImagePreviewUrl);
      }
      setCompanyImagePreviewUrl(null);

      if (session) {
        updateSession({
          ...session,
          user: {
            ...session.user,
            profile_completed: updatedProfile.is_complete,
            profile_path: updatedProfile.is_complete ? "/company/corpers" : "/company/profile",
            company_verification_status: updatedProfile.verification_status,
          },
        });
      }

      if (!isEditMode && updatedProfile.is_complete) {
        toast.success("Company profile submitted.");
        router.replace("/company/corpers");
        return;
      }

      await refetch();
      toast.success(isEditMode ? "Company profile changes saved." : "Company profile saved.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to save profile.");
    } finally {
      setIsSaving(false);
    }
  }

  const headerAside = (
    <div
      className={clsx(
        "w-full max-w-[220px] rounded-[28px] border border-white/12 bg-white/[0.08] p-4 backdrop-blur-xl",
        isProfileFieldHighlighted("company_image") && TEMPORARY_FIELD_ERROR_CLASS_NAME
      )}
    >
      <div className="relative overflow-hidden rounded-[24px] border border-white/10 bg-white/[0.06]">
        <div className="aspect-[4/3] w-full">
          {resolvedCompanyImageUrl ? (
            <img
              src={resolvedCompanyImageUrl}
              alt={companyDisplayName}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(124,217,161,0.35),rgba(9,32,19,0.94))] text-4xl font-semibold text-white">
              {getCompanyMonogram(companyDisplayName)}
            </div>
          )}
        </div>
      </div>
      <input
        ref={companyImageInputRef}
        id="company_image"
        name="company_image"
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        className="sr-only"
        onChange={handleCompanyImageChange}
        disabled={!canEditPhoto || isProcessingCompanyImage}
      />
      <p className="mt-4 text-[10px] uppercase tracking-[0.18em] text-white/45">Profile photo *</p>
      {canEditPhoto ? (
        <Button
          type="button"
          variant="secondary"
          className="mt-2 w-full"
          onClick={() => companyImageInputRef.current?.click()}
          disabled={isProcessingCompanyImage}
        >
          <Upload className="mr-2 h-4 w-4" />
          {isProcessingCompanyImage ? "Processing..." : "Upload photo"}
        </Button>
      ) : null}
    </div>
  );

  return (
    <DashboardShell role="company" title="Company profile" headerAside={headerAside}>
      {!profile && loading ? (
        <Card>
          <p className="text-sm text-mist">Loading your company profile...</p>
        </Card>
      ) : !profile ? (
        <Card>
          <p className="text-sm text-mist">Unable to load your company profile right now.</p>
        </Card>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <Card className="grid gap-6 bg-white/[0.01]">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="font-display text-xl text-white">Company Information</h2>
              <div className="flex flex-wrap gap-2">
                <Badge tone={verificationStatusTone}>{verificationStatusLabel}</Badge>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Company name", true)}</span>
                <Input
                  name="company_name"
                  placeholder="Company name"
                  value={formValues.company_name}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_name")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Company Registration Date")}</span>
                <Input
                  name="company_registration_date"
                  type="date"
                  value={formValues.company_registration_date}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_registration_date")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Company Registration Number", true)}</span>
                <Input
                  name="company_registration_number"
                  placeholder="e.g. RC12345"
                  value={formValues.company_registration_number}
                  onChange={handleFieldChange}
                  onBlur={handleCompanyRegistrationNumberBlur}
                  autoCapitalize="characters"
                  pattern="(?:RC|BN|IT|LP|LLP)[0-9]{5,10}"
                  title={COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE}
                  maxLength={13}
                  spellCheck={false}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_registration_number")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Tax Identification Number", true)}</span>
                <Input
                  name="tax_identification_number"
                  placeholder="Tax Identification Number"
                  value={formValues.tax_identification_number}
                  onChange={handleFieldChange}
                  inputMode="numeric"
                  pattern="[0-9]{10,13}"
                  title={TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE}
                  maxLength={13}
                  spellCheck={false}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("tax_identification_number")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <div className={GENERAL_DIV}>
                <span>{fieldLabel("State", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select one or more states"
                  values={formValues.company_location_state}
                  groups={STATE_OF_OPERATION_OPTIONS}
                  searchable
                  searchPlaceholder="Type to filter states"
                  summaryClassName={dropdownSummaryClassName(formValues.company_location_state)}
                  emptyStateText="No state matches your search."
                  onChange={(values) => updateFormValue("company_location_state", values)}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_location_state")}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("City", true)}</span>
                <Input
                  name="company_location_city"
                  placeholder="City"
                  value={formValues.company_location_city}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_location_city")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Company sector", true)}</span>
                <Select
                  name="company_sector"
                  value={formValues.company_sector}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_sector")}
                  className={selectClassName(formValues.company_sector)}
                  style={selectPlaceholderStyle(formValues.company_sector)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Select company sector
                  </option>
                  {COMPANY_SECTOR_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Organisation type", true)}</span>
                <Select
                  name="organization_type"
                  value={formValues.organization_type}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("organization_type")}
                  className={selectClassName(formValues.organization_type)}
                  style={selectPlaceholderStyle(formValues.organization_type)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Select organisation type
                  </option>
                  {ORGANIZATION_TYPE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                  <option value={CUSTOM_ORGANIZATION_TYPE_OPTION}>
                    {CUSTOM_ORGANIZATION_TYPE_OPTION}
                  </option>
                </Select>
              </label>

              {formValues.organization_type === CUSTOM_ORGANIZATION_TYPE_OPTION ? (
                <label className={GENERAL_LABEL}>
                  <span>{fieldLabel("Other organisation type", true)}</span>
                  <Input
                    name="organization_type_other"
                    placeholder="Enter organisation type"
                    value={formValues.organization_type_other}
                    onChange={handleFieldChange}
                    required
                    disabled={!canEditProfile}
                    hasError={isProfileFieldHighlighted("organization_type_other")}
                    className={PLACEHOLDER_CLASS_NAME}
                  />
                </label>
              ) : null}

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Number of office locations", true)}</span>
                <Input
                  name="office_location_count"
                  type="number"
                  min="1"
                  placeholder="Enter number of cities where you have offices"
                  value={formValues.office_location_count}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("office_location_count")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Number of staff", true)}</span>
                <Select
                  name="staff_count_range"
                  value={formValues.staff_count_range}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("staff_count_range")}
                  className={selectClassName(formValues.staff_count_range)}
                  style={selectPlaceholderStyle(formValues.staff_count_range)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Select number of staff range
                  </option>
                  {STAFF_COUNT_RANGE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              </label>

              <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                <span>{fieldLabel("Company Summary", true)}</span>
                <Textarea
                  name="desired_corper_description"
                  placeholder="Describe your company and what you do"
                  value={formValues.desired_corper_description}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_corper_description")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
            </div>
          </Card>

          <div className="mb-3" />

          <Card className="grid gap-6 bg-white/[0.01]">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="font-display text-xl text-white">PPA Information</h2>
              <div className="flex flex-wrap gap-2">
                <Badge tone={verificationStatusTone}>{verificationStatusLabel}</Badge>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className={GENERAL_DIV}>
                <span>{fieldLabel("Placement Type", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select one or more placement types"
                  values={formValues.placement_type}
                  groups={PLACEMENT_TYPE_OPTION_GROUPS}
                  summaryClassName={dropdownSummaryClassName(formValues.placement_type)}
                  onChange={(values) => updateFormValue("placement_type", values)}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("placement_type")}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Accommodation provided?", true)}</span>
                <Select
                  name="accommodation_provided"
                  value={formValues.accommodation_provided}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("accommodation_provided")}
                  className={selectClassName(formValues.accommodation_provided)}
                  style={selectPlaceholderStyle(formValues.accommodation_provided)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Select an option
                  </option>
                  {ACCOMMODATION_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("PPA Capacity", true)}</span>
                <Input
                  name="ppa_capacity"
                  type="number"
                  min="1"
                  placeholder="Number of corp members you can accomodate"
                  value={formValues.ppa_capacity}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("ppa_capacity")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("PPA support")}</span>
                <Select
                  name="ppa_support"
                  value={formValues.ppa_support}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("ppa_support")}
                  className={selectClassName(formValues.ppa_support)}
                  style={selectPlaceholderStyle(formValues.ppa_support)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Can you support PPA process with NYSC?
                  </option>
                  {PPA_SUPPORT_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              </label>

              <div className={GENERAL_DIV}>
                <span>{fieldLabel("Preferred states for PPA Placement", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select states where you can accept corp members"
                  values={formValues.preferred_deployment_states}
                  groups={STATE_OF_OPERATION_OPTIONS}
                  searchable
                  searchPlaceholder="Type to filter states"
                  summaryClassName={dropdownSummaryClassName(formValues.preferred_deployment_states)}
                  emptyStateText="No state matches your search."
                  onChange={handlePreferredDeploymentStatesChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("preferred_deployment_states")}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Monthly allowance offered", true)}</span>
                <Select
                  name="monthly_allowance_offered"
                  value={formValues.monthly_allowance_offered}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("monthly_allowance_offered")}
                  className={selectClassName(formValues.monthly_allowance_offered)}
                  style={selectPlaceholderStyle(formValues.monthly_allowance_offered)}
                >
                  <option value="" style={PLACEHOLDER_OPTION_STYLE}>
                    Select allowance range
                  </option>
                  {MONTHLY_ALLOWANCE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </Select>
              </label>
            </div>
          </Card>

          <div className="mb-3" />

          <Card className="grid gap-6 bg-white/[0.01]">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="font-display text-xl text-white">Contact Details</h2>
              <div className="flex flex-wrap gap-2">
                <Badge tone={verificationStatusTone}>{verificationStatusLabel}</Badge>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                <span>{fieldLabel("Head office address", true)}</span>
                <Input
                  name="head_office_address"
                  placeholder="Head office address"
                  value={formValues.head_office_address}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("head_office_address")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <div className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span>{fieldLabel("Company operating address", true)}</span>
                  <label className="inline-flex items-center gap-2 text-xs text-lime">
                    <input
                      type="checkbox"
                      checked={isCompanyAddressSameAsHeadOffice}
                      onChange={handleCompanyAddressSyncChange}
                      disabled={!canEditProfile}
                      className={CHECKBOX_CLASS_NAME}
                    />
                    <span>Same as Head office address?</span>
                  </label>
                </div>
                <Input
                  name="company_address"
                  placeholder="Company operating address"
                  value={formValues.company_address}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile || isCompanyAddressSameAsHeadOffice}
                  hasError={isProfileFieldHighlighted("company_address")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Director's fullname", true)}</span>
                <Input
                  name="directors_name"
                  placeholder="Director's fullname"
                  value={formValues.directors_name}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("directors_name")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Director's phone number", true)}</span>
                <Input
                  name="director_phone_number"
                  placeholder="e.g. +2348012345678"
                  value={formValues.director_phone_number}
                  onChange={handleFieldChange}
                  inputMode="tel"
                  maxLength={14}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("director_phone_number")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <div className={GENERAL_DIV}>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span>{fieldLabel("Contact fullname", true)}</span>
                  <label className="inline-flex items-center gap-2 text-xs text-lime">
                    <input
                      type="checkbox"
                      checked={isContactNameSameAsDirector}
                      onChange={handleContactNameSyncChange}
                      disabled={!canEditProfile}
                      className={CHECKBOX_CLASS_NAME}
                    />
                    <span>Same as director name?</span>
                  </label>
                </div>
                <Input
                  name="contact_name"
                  placeholder="Contact fullname"
                  value={formValues.contact_name}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile || isContactNameSameAsDirector}
                  hasError={isProfileFieldHighlighted("contact_name")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </div>
              <div className={GENERAL_DIV}>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span>{fieldLabel("Contact number", true)}</span>
                  <label className="inline-flex items-center gap-2 text-xs text-lime">
                    <input
                      type="checkbox"
                      checked={isContactPhoneSameAsDirector}
                      onChange={handleContactPhoneSyncChange}
                      disabled={!canEditProfile}
                      className={CHECKBOX_CLASS_NAME}
                    />
                    <span>Same as director phone number?</span>
                  </label>
                </div>
                <Input
                  name="contact_phone"
                  placeholder="+2348012345678"
                  value={formValues.contact_phone}
                  onChange={handleFieldChange}
                  inputMode="tel"
                  maxLength={14}
                  required
                  disabled={!canEditProfile || isContactPhoneSameAsDirector}
                  hasError={isProfileFieldHighlighted("contact_phone")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Contact email", true)}</span>
                <Input
                  name="contact_email"
                  type="email"
                  placeholder="contact@example.com"
                  value={formValues.contact_email}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("contact_email")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Company website")}</span>
                <Input
                  name="company_website"
                  type="url"
                  placeholder="https://example.com"
                  value={formValues.company_website}
                  onChange={handleFieldChange}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("company_website")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
            </div>
          </Card>

          <div className="mb-3" />

          <Card className="grid gap-6 bg-white/[0.01]">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="font-display text-xl text-white">Preferences</h2>
              <div className="flex flex-wrap gap-2">
                <Badge tone={verificationStatusTone}>{verificationStatusLabel}</Badge>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Desired qualifications", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select one or more qualifications"
                  values={formValues.desired_qualification}
                  groups={QUALIFICATION_OPTIONS}
                  exclusiveOption={ANY_QUALIFICATION_OPTION}
                  summaryClassName={dropdownSummaryClassName(formValues.desired_qualification)}
                  onChange={(values) => updateFormValue("desired_qualification", values)}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_qualification")}
                />
              </label>
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Desired field of study", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select one or more fields of study"
                  values={formValues.desired_field_of_study}
                  groups={fieldOfStudyOptions}
                  exclusiveOption={ANY_FIELD_OF_STUDY_OPTION}
                  searchable
                  searchPlaceholder="Type to filter fields of study"
                  summaryClassName={dropdownSummaryClassName(formValues.desired_field_of_study)}
                  emptyStateText="No fields of study match your search."
                  onChange={(values) => updateFormValue("desired_field_of_study", values)}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_field_of_study")}
                />
              </label>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Desired universities", true)}</span>
                <MultiSelectDropdown
                  placeholder="Select desired universities"
                  values={formValues.desired_university}
                  groups={DESIRED_UNIVERSITY_OPTIONS}
                  exclusiveOption={ANY_UNIVERSITY_OPTION}
                  searchable
                  searchPlaceholder="Type to filter universities"
                  summaryClassName={dropdownSummaryClassName(formValues.desired_university)}
                  emptyStateText="No university matches your search."
                  onChange={(values) => updateFormValue("desired_university", values)}
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_university")}
                />
              </label>

              <div className={GENERAL_DIV}>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span>{fieldLabel("Desired posting state", true)}</span>
                  <label className="inline-flex items-center gap-2 text-xs text-lime">
                    <input
                      type="checkbox"
                      checked={isDesiredPostingStateSameAsPreferred}
                      onChange={handleDesiredPostingStateSyncChange}
                      disabled={!canEditProfile}
                      className={CHECKBOX_CLASS_NAME}
                    />
                    <span>Same as Preferred states of deployment</span>
                  </label>
                </div>
                <MultiSelectDropdown
                  placeholder="Select desired posting states"
                  values={formValues.desired_posting_states}
                  groups={STATE_OF_OPERATION_OPTIONS}
                  searchable
                  searchPlaceholder="Type to filter states"
                  summaryClassName={dropdownSummaryClassName(formValues.desired_posting_states)}
                  emptyStateText="No state matches your search."
                  onChange={(values) => updateFormValue("desired_posting_states", values)}
                  disabled={!canEditProfile || isDesiredPostingStateSameAsPreferred}
                  hasError={isProfileFieldHighlighted("desired_posting_states")}
                />
              </div>

              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Desired skills", true)}</span>
                <Input
                  name="desired_skills"
                  placeholder="Desired skills"
                  value={formValues.desired_skills}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_skills")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
              <label className={GENERAL_LABEL}>
                <span>{fieldLabel("Desired age range", true)}</span>
                <Input
                  name="desired_age_range"
                  placeholder="e.g. 19 - 26"
                  value={formValues.desired_age_range}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_age_range")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>

              <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                <span>{fieldLabel("Desired experience", true)}</span>
                <Textarea
                  name="desired_experience"
                  placeholder="Desired experience"
                  value={formValues.desired_experience}
                  onChange={handleFieldChange}
                  required
                  disabled={!canEditProfile}
                  hasError={isProfileFieldHighlighted("desired_experience")}
                  className={PLACEHOLDER_CLASS_NAME}
                />
              </label>
            </div>
          </Card>

          <div className="mb-3" />

          <div className="flex items-center justify-end">
            <Button type="submit" disabled={isSaving || isProcessingCompanyImage || !canEditProfile}>
              {isSaving
                ? "Saving..."
                : isEditMode
                  ? "Save Changes"
                  : !canEditProfile
                    ? "Profile verified"
                    : "Submit"}
            </Button>
          </div>
        </form>
      )}
    </DashboardShell>
  );
}
