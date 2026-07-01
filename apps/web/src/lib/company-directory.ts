import { resolveMediaUrl } from "@/lib/media";

export type CompanyDirectorySummary = {
  id: string;
  company_name: string;
  company_image: string | null;
  location: string;
  company_sector: string;
  company_function: string;
  summary_description: string;
  match_score: number | null;
  match_reasons: string[];
  recommended: boolean;
};

export type CompanyDirectoryDetail = CompanyDirectorySummary & {
  company_location_state: string;
  company_location_city: string;
  desired_qualification: string;
  desired_age_range: string;
  desired_field_of_study: string;
  desired_university: string;
  desired_posting_states: string;
  desired_skills: string;
  desired_experience: string;
  corper_has_expressed_interest: boolean;
  company_has_expressed_interest: boolean;
};

export function getCompanyMonogram(name: string) {
  const source = name
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!source.length) {
    return "B";
  }

  return source.map((part) => part.charAt(0).toUpperCase()).join("");
}

export function formatCompanyDirectoryLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function getCompanyDirectoryImage(
  imageUrls: string[],
  seed: string,
  companyImage?: string | null
) {
  const uploadedImageUrl = resolveMediaUrl(companyImage);
  if (uploadedImageUrl) {
    return uploadedImageUrl;
  }

  if (imageUrls.length === 0) {
    return null;
  }

  const hash = seed.split("").reduce((total, character) => total + character.charCodeAt(0), 0);
  return imageUrls[hash % imageUrls.length];
}
