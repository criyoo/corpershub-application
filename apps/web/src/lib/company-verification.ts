type ValidationResult = {
  normalizedValue: string;
  error: string | null;
};

export const COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE =
  "Enter a valid company registration number in the format RC12345, BN12345, IT12345, LP12345, or LLP12345 without any spaces.";
export const TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE =
  "Enter a valid tax identification number with 10 to 13 digits.";

const COMPANY_REGISTRATION_NUMBER_PATTERN = /^(?:RC|BN|IT|LP|LLP)\d{5,10}$/;
const TAX_IDENTIFICATION_NUMBER_PATTERN = /^\d{10,13}$/;

export function normalizeCompanyRegistrationNumber(value: string | null | undefined) {
  return (value ?? "").trim().toUpperCase().replace(/[\s-]+/g, "");
}

export function normalizeTaxIdentificationNumber(value: string | null | undefined) {
  return (value ?? "").trim();
}

export function validateCompanyRegistrationNumber(value: string | null | undefined): ValidationResult {
  const normalizedValue = normalizeCompanyRegistrationNumber(value);
  if (!normalizedValue) {
    return {
      error: "Company registration number is required.",
      normalizedValue,
    };
  }

  if (!COMPANY_REGISTRATION_NUMBER_PATTERN.test(normalizedValue)) {
    return {
      error: COMPANY_REGISTRATION_NUMBER_ERROR_MESSAGE,
      normalizedValue,
    };
  }

  return {
    error: null,
    normalizedValue,
  };
}

export function validateTaxIdentificationNumber(value: string | null | undefined): ValidationResult {
  const normalizedValue = normalizeTaxIdentificationNumber(value);
  if (!normalizedValue) {
    return {
      error: "Tax identification number is required.",
      normalizedValue,
    };
  }

  if (!TAX_IDENTIFICATION_NUMBER_PATTERN.test(normalizedValue)) {
    return {
      error: TAX_IDENTIFICATION_NUMBER_ERROR_MESSAGE,
      normalizedValue,
    };
  }

  return {
    error: null,
    normalizedValue,
  };
}

export function formatCompanyVerificationStatus(status?: string | null) {
  switch (status) {
    case "verified":
      return "Verified";
    case "pending":
      return "Pending verification";
    case "rejected":
      return "Verification failed";
    default:
      return "Not verified";
  }
}

export function getCompanyVerificationTone(
  status?: string | null
): "neutral" | "warning" | "success" {
  switch (status) {
    case "verified":
      return "success";
    case "pending":
    case "rejected":
      return "warning";
    default:
      return "neutral";
  }
}

export function formatCompanyApprovalStatus(status?: string | null) {
  switch (status) {
    case "approved":
      return "Approved";
    case "pending":
      return "Pending";
    case "rejected":
      return "Rejected";
    default:
      return "Unsubmitted";
  }
}

export function getCompanyApprovalTone(status?: string | null): "neutral" | "warning" | "success" {
  switch (status) {
    case "approved":
      return "success";
    case "pending":
    case "rejected":
      return "warning";
    default:
      return "neutral";
  }
}
