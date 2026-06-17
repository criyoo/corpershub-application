"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ShieldCheck, Upload } from "lucide-react";
import { Suspense, type ChangeEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SearchableSelectDropdown } from "@/components/ui/searchable-select-dropdown";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { courseCatalogHasCourse, toCourseOptionGroups, type CourseCatalogResponse } from "@/lib/course-catalog";
import { resolveMediaUrl } from "@/lib/media";
import {
  isKnownNigerianDegree,
  NIGERIAN_DEGREE_GROUPS,
  NIGERIAN_STATES,
  CORPER_BATCHES,
  CORPER_GENDERS,
  CORPER_STREAMS,
} from "@/lib/nigerian-reference-data";
import { formatVerificationStatus } from "@/lib/verification";
import {
  isNigerianUniversity,
  NIGERIAN_UNIVERSITY_GROUPS,
} from "@/lib/nigerian-universities";

type CorperProfile = {
  id: string;
  email: string;
  full_name: string;
  first_name: string;
  middle_name: string;
  surname: string;
  date_of_birth: string | null;
  gender: string;
  state_of_origin: string;
  country_of_birth: string;
  posting_location_state: string;
  batch: string;
  stream: string;
  university_matriculation_number: string;
  field_of_study: string;
  degree: string;
  university: string;
  graduation_year: number | null;
  profile_photo: string | null;
  nin_number: string;
  mobile_number: string;
  nysc_callup_number: string;
  nysc_state_code: string;
  skill: string;
  technical_skills: string;
  soft_skills: string;
  languages_spoken: string;
  available_date: string | null;
  bio: string;
  preferred_sector: string;
  preferred_organization_type: string;
  preferred_placement_type: string;
  preferred_monthly_allowance: string;
  preferred_organization_experience: string;
  masked_nin_number: string;
  masked_callup_number: string;
  masked_state_code: string;
  verification_status: string;
  biodata_verification_status: string;
  nin_verification_status: string;
  nysc_callup_verification_status: string;
  nysc_state_code_verification_status: string;
  is_complete: boolean;
  profile_fields_complete: boolean;
  terms_accepted: boolean;
};

type FormValues = {
  first_name: string;
  middle_name: string;
  surname: string;
  date_of_birth: string;
  gender: string;
  state_of_origin: string;
  country_of_birth: string;
  posting_location_state: string;
  batch: string;
  stream: string;
  university_matriculation_number: string;
  field_of_study: string;
  degree: string;
  university: string;
  graduation_year: string;
  mobile_number: string;
  technical_skills: string;
  soft_skills: string;
  languages_spoken: string;
  available_date: string;
  bio: string;
  preferred_sector: string;
  preferred_organization_type: string;
  preferred_placement_type: string;
  preferred_monthly_allowance: string;
  preferred_organization_experience: string;
};

const EMPTY_FORM_VALUES: FormValues = {
  first_name: "",
  middle_name: "",
  surname: "",
  date_of_birth: "",
  gender: "",
  state_of_origin: "",
  country_of_birth: "",
  posting_location_state: "",
  batch: "",
  stream: "",
  university_matriculation_number: "",
  field_of_study: "",
  degree: "",
  university: "",
  graduation_year: "",
  mobile_number: "",
  technical_skills: "",
  soft_skills: "",
  languages_spoken: "",
  available_date: "",
  bio: "",
  preferred_sector: "",
  preferred_organization_type: "",
  preferred_placement_type: "",
  preferred_monthly_allowance: "",
  preferred_organization_experience: "",
};

const OTHER_UNIVERSITY_OPTION = "__other__";
const OTHER_FIELD_OF_STUDY_OPTION = "__other_field_of_study__";
const PREFERRED_SECTOR_OPTIONS = [
  "Technology & IT",
  "Financial Services & Banking",
  "Consulting & Professional Services",
  "Media & Communications",
  "E-commerce & Retail",
  "Logistics & Supply Chain",
  "Energy & Utilities",
  "Real Estate & Construction",
  "Education & Training",
  "Healthcare & Pharmaceuticals",
  "NGO & Non-Profit",
  "Government & Public Sector",
  "Agriculture & Agribusiness",
  "Manufacturing & Production",
  "Hospitality & Tourism",
  "Legal & Compliance",
  "Creative & Design",
  "Research & Development",
  "Sports & Recreation",
  "Security & Investigation",
  "Transport & Aviation",
  "Insurance & Life Assurance",
  "Social Work & Community",
];
const PREFERRED_ORGANIZATION_TYPE_OPTIONS = [
  "Private Company",
  "Public Company",
  "Government Agency",
  "Non-Government Organization (NGO)",
  "Public Education Institution",
  "Private Education Institution",
  "International Organization",
  "Others",
];
const PREFERRED_PLACEMENT_TYPE_OPTIONS = [
  "Full-time / On-Site",
  "Full-time / Remote",
  "Full-time / Hybrid",
  "Part-Time / On-Site",
  "Part-Time / Remote",
  "Part-Time / Hybrid",
];
const PREFERRED_MONTHLY_ALLOWANCE_OPTIONS = [
  "None",
  "Below N25,000",
  "N25,000-N50,000",
  "N50,000-N100,000",
  "Above N100,000",
  "Negotiable",
];
const CURRENT_YEAR = new Date().getFullYear();
const GRADUATION_YEAR_OPTIONS = Array.from({ length: 2050 - 1973 + 1 }, (_, index) => String(1973 + index));
const PROFILE_GENDER_OPTIONS = CORPER_GENDERS.filter((gender) => gender.value !== "other");
const CORPER_GENDER_VALUES = new Set(PROFILE_GENDER_OPTIONS.map((gender) => gender.value));
type CorperGenderValue = (typeof PROFILE_GENDER_OPTIONS)[number]["value"];

function normalizeCorperGenderForForm(value: string | null | undefined) {
  const normalized = value?.trim().toLowerCase() ?? "";
  return CORPER_GENDER_VALUES.has(normalized as CorperGenderValue) ? normalized : "";
}

function normalizeCorperMobileForDisplay(value: string) {
  const normalized = value.trim();
  if (!normalized) {
    return "";
  }
  if (normalized.startsWith("+234")) {
    return normalized;
  }
  if (/^0\d{10}$/.test(normalized)) {
    return `+234${normalized.slice(1)}`;
  }
  return normalized;
}

function normalizeCorperMobileInput(value: string) {
  const digits = value.replace(/\D/g, "");
  if (!digits) {
    return "";
  }

  let subscriberDigits = digits;
  if (subscriberDigits.startsWith("234")) {
    subscriberDigits = subscriberDigits.slice(3);
  } else if (subscriberDigits.startsWith("0")) {
    subscriberDigits = subscriberDigits.slice(1);
  }

  return `+234${subscriberDigits.slice(0, 10)}`;
}

function mapProfileToForm(profile: CorperProfile): FormValues {
  return {
    first_name: profile.first_name ?? "",
    middle_name: profile.middle_name ?? "",
    surname: profile.surname ?? "",
    date_of_birth: profile.date_of_birth ?? "",
    gender: normalizeCorperGenderForForm(profile.gender),
    state_of_origin: profile.state_of_origin ?? "",
    country_of_birth: profile.country_of_birth ?? "",
    posting_location_state: profile.posting_location_state ?? "",
    batch: profile.batch ?? "",
    stream: profile.stream ?? "",
    university_matriculation_number: profile.university_matriculation_number ?? "",
    field_of_study: profile.field_of_study ?? "",
    degree: profile.degree ?? "",
    university: profile.university ?? "",
    graduation_year: profile.graduation_year ? String(profile.graduation_year) : "",
    mobile_number: normalizeCorperMobileForDisplay(profile.mobile_number ?? ""),
    technical_skills: profile.technical_skills ?? "",
    soft_skills: profile.soft_skills ?? "",
    languages_spoken: profile.languages_spoken ?? "",
    available_date: profile.available_date ?? "",
    bio: profile.bio ?? "",
    preferred_sector: profile.preferred_sector ?? "",
    preferred_organization_type: profile.preferred_organization_type ?? "",
    preferred_placement_type: profile.preferred_placement_type ?? "",
    preferred_monthly_allowance: profile.preferred_monthly_allowance ?? "",
    preferred_organization_experience: profile.preferred_organization_experience ?? "",
  };
}

function getInitials(value: string) {
  const parts = value
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!parts.length) {
    return "C";
  }

  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

function getMissingProfileFields(
  formValues: FormValues,
  hasProfilePhoto: boolean
) {
  const missingFields: string[] = [];

  if (!formValues.first_name.trim()) {
    missingFields.push("first name");
  }
  if (!formValues.surname.trim()) {
    missingFields.push("surname");
  }
  if (!formValues.date_of_birth.trim()) {
    missingFields.push("date of birth");
  }
  if (!formValues.posting_location_state.trim()) {
    missingFields.push("posting state");
  }
  if (!formValues.batch.trim()) {
    missingFields.push("batch");
  }
  if (!formValues.stream.trim()) {
    missingFields.push("stream");
  }
  if (!formValues.field_of_study.trim()) {
    missingFields.push("field of study");
  }
  if (!formValues.degree.trim()) {
    missingFields.push("degree");
  }
  if (!formValues.university.trim()) {
    missingFields.push("university");
  }
  if (!formValues.graduation_year.trim()) {
    missingFields.push("graduation year");
  }
  if (!formValues.mobile_number.trim()) {
    missingFields.push("mobile number");
  }
  if (!formValues.technical_skills.trim()) {
    missingFields.push("technical skills");
  }
  if (!formValues.soft_skills.trim()) {
    missingFields.push("soft skills");
  }
  if (!formValues.languages_spoken.trim()) {
    missingFields.push("languages spoken");
  }
  if (!formValues.available_date.trim()) {
    missingFields.push("available date");
  }
  if (!formValues.bio.trim()) {
    missingFields.push("bio");
  }
  if (!hasProfilePhoto) {
    missingFields.push("profile photo");
  }

  return missingFields;
}

export default function CorperProfilePage() {
  return (
    <Suspense fallback={null}>
      <CorperProfilePageContent />
    </Suspense>
  );
}

function CorperProfilePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hydrated, session, updateSession } = useAuth();
  const protectedQueryEnabled = hydrated && Boolean(session) && session?.user.role === "corper";
  const { data, refetch, loading } = useApiQuery<CorperProfile>("/corpers/me/", protectedQueryEnabled);
  const { data: courseCatalog, loading: courseCatalogLoading } =
    useApiQuery<CourseCatalogResponse>("/common/course-catalog/");
  const [profile, setProfile] = useState<CorperProfile | null>(null);
  const [formValues, setFormValues] = useState<FormValues>(EMPTY_FORM_VALUES);
  const [selectedProfilePhoto, setSelectedProfilePhoto] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const photoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!data) {
      return;
    }
    setProfile(data);
    setFormValues(mapProfileToForm(data));
  }, [data]);

  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl);
      }
    };
  }, [photoPreviewUrl]);

  const documentsVerified =
    profile?.biodata_verification_status === "verified" &&
    profile?.nin_verification_status === "verified" &&
    profile?.nysc_callup_verification_status === "verified" &&
    profile?.nysc_state_code_verification_status === "verified";
  const isComplete = profile?.is_complete ?? false;
  const isEditMode = searchParams.get("edit") === "1";
  const canEditFullProfile = documentsVerified && !isComplete;
  const canEditLimitedProfile = documentsVerified && isComplete && isEditMode;
  const canEditProfile = canEditFullProfile || canEditLimitedProfile;
  const canEditGender = canEditFullProfile || canEditLimitedProfile;
  const canEditPostingState = canEditFullProfile || canEditLimitedProfile;
  const canEditPhoto = canEditFullProfile || canEditLimitedProfile;
  const selectedUniversityOption = formValues.university
    ? isNigerianUniversity(formValues.university)
      ? formValues.university
      : OTHER_UNIVERSITY_OPTION
    : "";
  const selectedUniversityDisplayValue =
    selectedUniversityOption === OTHER_UNIVERSITY_OPTION ? "Others" : selectedUniversityOption;
  const selectedDegreeOption = formValues.degree
    ? isKnownNigerianDegree(formValues.degree)
      ? formValues.degree
      : ""
    : "";
  const fieldOfStudyGroups = toCourseOptionGroups(
    courseCatalog?.fields ?? [],
    formValues.field_of_study ? [formValues.field_of_study] : []
  );
  const selectedFieldOfStudyOption = formValues.field_of_study
    ? courseCatalogHasCourse(courseCatalog?.fields ?? [], formValues.field_of_study)
      ? formValues.field_of_study
      : OTHER_FIELD_OF_STUDY_OPTION
    : "";
  const selectedFieldOfStudyDisplayValue =
    selectedFieldOfStudyOption === OTHER_FIELD_OF_STUDY_OPTION ? "Others" : selectedFieldOfStudyOption;
  const showCustomUniversityField = selectedUniversityOption === OTHER_UNIVERSITY_OPTION;
  const showCustomFieldOfStudyField = selectedFieldOfStudyOption === OTHER_FIELD_OF_STUDY_OPTION;
  const resolvedPhotoUrl = photoPreviewUrl || resolveMediaUrl(profile?.profile_photo);
  const displayName =
    [formValues.first_name, formValues.middle_name, formValues.surname]
      .map((part) => part.trim())
      .filter(Boolean)
      .join(" ") ||
    profile?.full_name ||
    profile?.email ||
    session?.user.email ||
    "Corper";
  const titleBadge =
    documentsVerified ? (
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.08] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-lime">
            {documentsVerified ? "Verified" : formatVerificationStatus(profile.verification_status)}
          </div>
        </div>
        {!documentsVerified ? (
          <div className="rounded-[24px] border border-[#BEE3CA] bg-[linear-gradient(135deg,rgba(31,183,102,0.18),rgba(236,248,240,0.12))] px-5 py-4 text-sm text-white">
            Complete biodata, NIN, NYSC call-up, and NYSC state code verification before editing your profile.
            <Link href="/corper/verification" className="ml-2 font-semibold text-lime transition hover:text-white">
              Open verification center
            </Link>
          </div>
        ) : canEditLimitedProfile ? (
          <div className="rounded-[24px] border border-white/10 bg-white/[0.05] px-5 py-4 text-sm text-mist">
            Only <span className="font-semibold text-white">Gender</span>, <span className="font-semibold text-white">Posting state</span>, <span className="font-semibold text-white">technical skills</span>, <span className="font-semibold text-white">soft skills</span>, <span className="font-semibold text-white">languages spoken</span>, <span className="font-semibold text-white">available date</span>, <span className="font-semibold text-white">Bio</span>, <span className="font-semibold text-white">Photo</span>, and <span className="font-semibold text-white">preferred organisation</span> fields can be updated here. Contact admin/support team to change the remaining profile fields.
          </div>
        ) : null}
      </div>
    ) : null;
  const headerActions = (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => router.back()}
        className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-3 py-1 text-sm text-mist transition hover:border-lime/90 hover:bg-white/[0.12] hover:text-white"
      >
        <ArrowLeft className="h-4 w-6" />
        Back
      </button>
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-3 py-1 text-sm text-mist transition hover:border-lime/90 hover:bg-white/[0.12] hover:text-white"
      >
        <ArrowLeft className="h-4 w-6" />
        Home
      </Link>
    </div>
  );

  function handleFieldChange(
    event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = event.target;
    setFormValues((current) => ({
      ...current,
      [name]: name === "mobile_number" ? normalizeCorperMobileInput(value) : value,
    }));
  }

  function handleUniversityChange(value: string) {
    setFormValues((current) => ({
      ...current,
      university:
        value === OTHER_UNIVERSITY_OPTION
          ? isNigerianUniversity(current.university)
            ? ""
            : current.university
          : value,
    }));
  }

  function handleFieldOfStudyChange(value: string) {
    setFormValues((current) => ({
      ...current,
      field_of_study:
        value === OTHER_FIELD_OF_STUDY_OPTION
          ? courseCatalogHasCourse(courseCatalog?.fields ?? [], current.field_of_study)
            ? ""
            : current.field_of_study
          : value,
    }));
  }

  function handleProfilePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    if (!canEditPhoto) {
      return;
    }

    const file = event.target.files?.[0] ?? null;
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
    }

    if (!file) {
      setSelectedProfilePhoto(null);
      setPhotoPreviewUrl(null);
      return;
    }

    setSelectedProfilePhoto(file);
    setPhotoPreviewUrl(URL.createObjectURL(file));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile || !canEditProfile) {
      return;
    }

    const formData = new FormData();
    if (canEditFullProfile) {
      const missingFields = getMissingProfileFields(
        formValues,
        Boolean(selectedProfilePhoto || profile.profile_photo)
      );
      if (missingFields.length > 0) {
        toast.error(`Complete all profile fields before saving: <${missingFields.join(", ")}>.`);
        return;
      }

      formData.set("posting_location_state", formValues.posting_location_state.trim());
      formData.set("batch", formValues.batch.trim());
      formData.set("stream", formValues.stream.trim());
      formData.set("field_of_study", formValues.field_of_study.trim());
      formData.set("degree", formValues.degree.trim());
      formData.set("university", formValues.university.trim());
      formData.set("technical_skills", formValues.technical_skills.trim());
      formData.set("soft_skills", formValues.soft_skills.trim());
      formData.set("languages_spoken", formValues.languages_spoken.trim());
      formData.set("available_date", formValues.available_date.trim());
      formData.set("bio", formValues.bio.trim());
      formData.set("preferred_sector", formValues.preferred_sector.trim());
      formData.set("preferred_organization_type", formValues.preferred_organization_type.trim());
      formData.set("preferred_placement_type", formValues.preferred_placement_type.trim());
      formData.set("preferred_monthly_allowance", formValues.preferred_monthly_allowance.trim());
      formData.set(
        "preferred_organization_experience",
        formValues.preferred_organization_experience.trim()
      );

      if (formValues.graduation_year.trim()) {
        formData.set("graduation_year", formValues.graduation_year.trim());
      }
    } else {
      formData.set("gender", formValues.gender.trim());
      formData.set("posting_location_state", formValues.posting_location_state.trim());
      formData.set("technical_skills", formValues.technical_skills.trim());
      formData.set("soft_skills", formValues.soft_skills.trim());
      formData.set("languages_spoken", formValues.languages_spoken.trim());
      formData.set("available_date", formValues.available_date.trim());
      formData.set("bio", formValues.bio.trim());
      formData.set("preferred_sector", formValues.preferred_sector.trim());
      formData.set("preferred_organization_type", formValues.preferred_organization_type.trim());
      formData.set("preferred_placement_type", formValues.preferred_placement_type.trim());
      formData.set("preferred_monthly_allowance", formValues.preferred_monthly_allowance.trim());
      formData.set(
        "preferred_organization_experience",
        formValues.preferred_organization_experience.trim()
      );
    }

    if (selectedProfilePhoto) {
      formData.set("profile_photo", selectedProfilePhoto);
    }

    setIsSaving(true);
    try {
      const updatedProfile = await apiFetch<CorperProfile>("/corpers/me/", {
        method: "PATCH",
        formData: true,
        body: formData,
      });

      setProfile(updatedProfile);
      setFormValues(mapProfileToForm(updatedProfile));
      setSelectedProfilePhoto(null);
      if (photoInputRef.current) {
        photoInputRef.current.value = "";
      }
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl);
      }
      setPhotoPreviewUrl(null);

      if (session) {
        updateSession({
          ...session,
          user: {
            ...session.user,
            profile_completed: updatedProfile.is_complete,
          },
        });
      }

      await refetch();
      window.dispatchEvent(new Event("corper-profile-updated"));
      if (canEditLimitedProfile) {
        toast.success("Profile Saved successfully, you can now browse companies profile", {
          duration: 3000,
        });
      } else {
        toast.success("Profile Saved successfully, you can now browse companies profile", {
          duration: 3000,
        });
        router.push(session?.user.needs_subscription_selection ? "/corper/billing" : "/corper/companies");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to save profile.");
    } finally {
      setIsSaving(false);
    }
  }

  const headerAside = (
    <div className="w-full max-w-[204px] rounded-[28px] border border-white/12 bg-white/[0.08] p-4 backdrop-blur-xl">
      <div className="relative overflow-hidden rounded-[24px] border border-white/10 bg-white/[0.06]">
        <div className="aspect-square w-full">
          {resolvedPhotoUrl ? (
            <img
              src={resolvedPhotoUrl}
              alt={displayName}
              className="h-full w-full object-cover object-[center_18%]"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(190,227,202,0.35),rgba(17,38,28,0.92))] text-4xl font-semibold text-white">
              {getInitials(displayName)}
            </div>
          )}
        </div>
      </div>
      <input
        ref={photoInputRef}
        id="profile_photo"
        name="profile_photo"
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        className="sr-only"
        onChange={handleProfilePhotoChange}
        disabled={!canEditPhoto}
      />
      {canEditPhoto ? (
        <Button
          type="button"
          variant="secondary"
          className="mt-4 w-full"
          onClick={() => photoInputRef.current?.click()}
        >
          <Upload className="mr-2 h-4 w-4" />
          Edit
        </Button>
      ) : null}
    </div>
  );

  return (
    <DashboardShell
      role="corper"
      title=""
      headerLabel={null}
      titleBadge={titleBadge}
      headerActions={headerActions}
      headerAside={headerAside}
    >
      {!profile && loading ? (
        <Card>
          <p className="text-sm text-mist">Loading your profile...</p>
        </Card>
      ) : !profile ? (
        <Card>
          <p className="text-sm text-mist">Unable to load your profile right now.</p>
        </Card>
      ) : !profile.terms_accepted ? (
        <Card className="grid gap-4">
          <div className="grid gap-2">
            <p className="text-xs uppercase tracking-[0.22em] text-lime">Legal agreement required</p>
            <h2 className="font-display text-2xl text-white">
              Accept every legal document before your profile unlocks
            </h2>
            <p className="text-sm text-mist">
              Your corper profile stays blocked until all required legal checkboxes are accepted.
            </p>
          </div>
          <div>
            <Link
              href="/corper/profile/terms"
              className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#1FB766_0%,#118A48_100%)] px-5 py-2.5 text-sm font-semibold text-[#E6D28C] shadow-[0_18px_35px_rgba(17,138,72,0.28)] transition duration-200 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-lime focus:ring-offset-2 focus:ring-offset-ink"
            >
              Review legal documents
            </Link>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          <form onSubmit={handleSubmit}>
            <Card className="grid gap-8">
              <section className="grid gap-4">
                <h2 className="text-base font-semibold text-white">Corper Verification Status</h2>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-[24px] border border-white/10 bg-white/[0.04] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-lime">NIN status</p>
                    <p className="mt-3 text-sm text-white">
                      {formatVerificationStatus(profile.nin_verification_status)}
                    </p>
                    {profile.masked_nin_number ? (
                      <p className="mt-2 text-xs text-slate-400">Stored value: {profile.masked_nin_number}</p>
                    ) : (
                      <p className="mt-2 text-xs text-slate-400">No NIN submitted yet.</p>
                    )}
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-white/[0.04] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-lime">NYSC call-up status</p>
                    <p className="mt-3 text-sm text-white">
                      {formatVerificationStatus(profile.nysc_callup_verification_status)}
                    </p>
                    {profile.masked_callup_number ? (
                      <p className="mt-2 text-xs text-slate-400">Stored value: {profile.masked_callup_number}</p>
                    ) : (
                      <p className="mt-2 text-xs text-slate-400">No call-up number submitted yet.</p>
                    )}
                  </div>
                  <div className="rounded-[24px] border border-white/10 bg-white/[0.04] px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.22em] text-lime">NYSC state code status</p>
                    <p className="mt-3 text-sm text-white">
                      {formatVerificationStatus(profile.nysc_state_code_verification_status)}
                    </p>
                    {profile.masked_state_code ? (
                      <p className="mt-2 text-xs text-slate-400">Stored value: {profile.masked_state_code}</p>
                    ) : (
                      <p className="mt-2 text-xs text-slate-400">No state code submitted yet.</p>
                    )}
                  </div>
                </div>
              </section>

              <section className="grid gap-4">
                <h2 className="text-base font-semibold text-white">Corper Details</h2>
                <div className="grid gap-4 md:grid-cols-6">
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>NIN Number</span>
                    <Input
                      value={profile.nin_number}
                      disabled
                      placeholder="Approved NIN will appear here"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>NYSC Call-Up Number</span>
                    <Input
                      value={profile.nysc_callup_number}
                      disabled
                      placeholder="Approved call-up number will appear here"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>NYSC State Code</span>
                    <Input
                      value={profile.nysc_state_code}
                      disabled
                      placeholder="Approved state code will appear here"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>First name</span>
                    <Input
                      name="first_name"
                      placeholder="First name"
                      value={formValues.first_name}
                      onChange={handleFieldChange}
                      required
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>Middle name</span>
                    <Input
                      name="middle_name"
                      placeholder="Middle name"
                      value={formValues.middle_name}
                      onChange={handleFieldChange}
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>Surname</span>
                    <Input
                      name="surname"
                      placeholder="Surname"
                      value={formValues.surname}
                      onChange={handleFieldChange}
                      required
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Date of birth</span>
                    <Input
                      name="date_of_birth"
                      type="date"
                      value={formValues.date_of_birth}
                      onChange={handleFieldChange}
                      required
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Gender</span>
                    <Select
                      name="gender"
                      value={formValues.gender}
                      onChange={handleFieldChange}
                      disabled
                    >
                      <option value="">Select gender</option>
                      {PROFILE_GENDER_OPTIONS.map((gender) => (
                        <option key={gender.value} value={gender.value}>
                          {gender.label}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>State of origin</span>
                    <Input
                      name="state_of_origin"
                      placeholder="State of origin"
                      value={formValues.state_of_origin}
                      onChange={handleFieldChange}
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Country of birth</span>
                    <Input
                      name="country_of_birth"
                      placeholder="Country of birth"
                      value={formValues.country_of_birth}
                      onChange={handleFieldChange}
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>University Matriculation Number</span>
                    <Input
                      name="university_matriculation_number"
                      placeholder="Verified matriculation number will appear here"
                      value={formValues.university_matriculation_number}
                      onChange={handleFieldChange}
                      disabled
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Posting state</span>
                    <Select
                      name="posting_location_state"
                      value={formValues.posting_location_state}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditPostingState}
                    >
                      <option value="">Select posting state</option>
                      {NIGERIAN_STATES.map((state) => (
                        <option key={state} value={state}>
                          {state}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Batch</span>
                    <Select
                      name="batch"
                      value={formValues.batch}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditFullProfile}
                    >
                      <option value="">Select batch</option>
                      {CORPER_BATCHES.map((batch) => (
                        <option key={batch.value} value={batch.value}>
                          {batch.label}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Stream</span>
                    <Select
                      name="stream"
                      value={formValues.stream}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditFullProfile}
                    >
                      <option value="">Select stream</option>
                      {CORPER_STREAMS.map((stream) => (
                        <option key={stream.value} value={stream.value}>
                          {stream.label}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Email address</span>
                    <Input
                      value={profile?.email ?? session?.user.email ?? ""}
                      disabled
                      placeholder="Email address"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Mobile number</span>
                    <Input
                      name="mobile_number"
                      placeholder="As registered in NIN records e.g. +2348012345678"
                      value={formValues.mobile_number}
                      onChange={handleFieldChange}
                      inputMode="tel"
                      maxLength={14}
                      required
                      disabled={!canEditFullProfile}
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Field of study</span>
                    <SearchableSelectDropdown
                      placeholder={courseCatalogLoading ? "Loading fields of study..." : "Select your field of study"}
                      value={selectedFieldOfStudyOption}
                      displayValue={selectedFieldOfStudyDisplayValue}
                      onChange={handleFieldOfStudyChange}
                      disabled={!canEditFullProfile || courseCatalogLoading}
                      groups={[
                        ...fieldOfStudyGroups.map((group) => ({
                          label: group.label,
                          options: group.options.map((course) => ({
                            label: course,
                            value: course,
                          })),
                        })),
                        {
                          label: "Other",
                          options: [{ label: "Others", value: OTHER_FIELD_OF_STUDY_OPTION }],
                        },
                      ]}
                      emptyStateText="No fields of study match your search."
                      searchPlaceholder="Search for your field of study"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Highest Degree</span>
                    <Select
                      name="degree"
                      value={selectedDegreeOption}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditFullProfile}
                    >
                      <option value="">Select highest degree</option>
                      {NIGERIAN_DEGREE_GROUPS.map((group) => (
                        <optgroup key={group.label} label={group.label}>
                          {group.degrees.map((degree) => (
                            <option key={degree} value={degree}>
                              {degree}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </Select>
                  </label>
                  {showCustomFieldOfStudyField ? (
                    <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-6">
                      <span>Other field of study</span>
                      <Input
                        name="field_of_study"
                        placeholder="Enter your course of study"
                        value={formValues.field_of_study}
                        onChange={handleFieldChange}
                        required
                        disabled={!canEditFullProfile}
                      />
                    </label>
                  ) : null}
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>University</span>
                    <SearchableSelectDropdown
                      placeholder="Select your university"
                      value={selectedUniversityOption}
                      displayValue={selectedUniversityDisplayValue}
                      onChange={handleUniversityChange}
                      disabled={!canEditFullProfile}
                      groups={[
                        ...NIGERIAN_UNIVERSITY_GROUPS.map((group) => ({
                          label: group.label,
                          options: group.universities.map((university) => ({
                            label: university,
                            value: university,
                          })),
                        })),
                        {
                          label: "Other",
                          options: [{ label: "Others", value: OTHER_UNIVERSITY_OPTION }],
                        },
                      ]}
                      emptyStateText="No universities match your search."
                      searchPlaceholder="Search for your university"
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Graduation Year</span>
                    <Select
                      name="graduation_year"
                      value={formValues.graduation_year}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditFullProfile}
                    >
                      <option value="">Select graduation year</option>
                      {GRADUATION_YEAR_OPTIONS.map((year) => (
                        <option key={year} value={year} disabled={Number(year) > CURRENT_YEAR}>
                          {year}
                        </option>
                      ))}
                    </Select>
                  </label>
                  {showCustomUniversityField ? (
                    <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-6">
                      <span>Other university</span>
                      <Input
                        name="university"
                        placeholder="Enter your university"
                        value={formValues.university}
                        onChange={handleFieldChange}
                        required
                        disabled={!canEditFullProfile}
                      />
                    </label>
                  ) : null}
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Technical Skills</span>
                    <Input
                      name="technical_skills"
                      placeholder="Technical skills"
                      value={formValues.technical_skills}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditProfile}
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Soft Skills</span>
                    <Input
                      name="soft_skills"
                      placeholder="Soft skills"
                      value={formValues.soft_skills}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditProfile}
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Languages Spoken</span>
                    <Input
                      name="languages_spoken"
                      placeholder="Languages spoken"
                      value={formValues.languages_spoken}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditProfile}
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-3">
                    <span>Available Date</span>
                    <Input
                      name="available_date"
                      type="date"
                      value={formValues.available_date}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditProfile}
                    />
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-6">
                    <span>Bio</span>
                    <Textarea
                      name="bio"
                      placeholder="Bio"
                      value={formValues.bio}
                      onChange={handleFieldChange}
                      required
                      disabled={!canEditProfile}
                    />
                  </label>
                </div>
              </section>

              <section className="grid gap-4">
                <h2 className="text-base font-semibold text-white">Preferred Organisation</h2>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45">
                    <span>Prefered Industry/Sector</span>
                    <Select
                      name="preferred_sector"
                      value={formValues.preferred_sector}
                      onChange={handleFieldChange}
                      disabled={!canEditProfile}
                    >
                      <option value="">Select preferred industry/sector</option>
                      {PREFERRED_SECTOR_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45">
                    <span>Preferred Organisation type</span>
                    <Select
                      name="preferred_organization_type"
                      value={formValues.preferred_organization_type}
                      onChange={handleFieldChange}
                      disabled={!canEditProfile}
                    >
                      <option value="">Select preferred organisation type</option>
                      {PREFERRED_ORGANIZATION_TYPE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45">
                    <span>Preferred Placement type</span>
                    <Select
                      name="preferred_placement_type"
                      value={formValues.preferred_placement_type}
                      onChange={handleFieldChange}
                      disabled={!canEditProfile}
                    >
                      <option value="">Select preferred placement type</option>
                      {PREFERRED_PLACEMENT_TYPE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45">
                    <span>Preferred Monthly allowance</span>
                    <Select
                      name="preferred_monthly_allowance"
                      value={formValues.preferred_monthly_allowance}
                      onChange={handleFieldChange}
                      disabled={!canEditProfile}
                    >
                      <option value="">Select preferred monthly allowance</option>
                      {PREFERRED_MONTHLY_ALLOWANCE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </Select>
                  </label>
                  <label className="grid gap-1.5 text-sm text-mist [&>span:first-child]:text-[10px] [&>span:first-child]:uppercase [&>span:first-child]:tracking-[0.18em] [&>span:first-child]:text-white/45 [&>div>span:first-child]:text-[10px] [&>div>span:first-child]:uppercase [&>div>span:first-child]:tracking-[0.18em] [&>div>span:first-child]:text-white/45 md:col-span-2">
                    <span>Experience</span>
                    <Textarea
                      name="preferred_organization_experience"
                      placeholder="Describe your experience"
                      value={formValues.preferred_organization_experience}
                      onChange={handleFieldChange}
                      disabled={!canEditProfile}
                    />
                  </label>
                </div>
              </section>

              <div className="flex flex-col gap-3 border-t border-white/10 pt-4 md:flex-row md:items-center md:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="submit" disabled={isSaving || !canEditProfile}>
                    {isSaving ? "Saving..." : canEditLimitedProfile ? "Save changes" : !canEditProfile ? "Profile locked" : "Next"}
                  </Button>
                </div>
              </div>
            </Card>
          </form>
        </div>
      )}
    </DashboardShell>
  );
}
