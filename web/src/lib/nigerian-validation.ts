const NIGERIAN_MOBILE_PREFIXES = new Set([
  "0701",
  "0702",
  "0703",
  "0704",
  "0705",
  "0706",
  "0707",
  "0708",
  "0709",
  "07025",
  "07026",
  "07027",
  "07028",
  "07029",
  "0802",
  "0803",
  "0804",
  "0805",
  "0806",
  "0807",
  "0808",
  "0809",
  "0810",
  "0811",
  "0812",
  "0813",
  "0814",
  "0815",
  "0816",
  "0817",
  "0818",
  "0819",
  "0901",
  "0902",
  "0903",
  "0904",
  "0905",
  "0906",
  "0907",
  "0908",
  "0909",
  "0911",
  "0912",
  "0913",
  "0915",
  "0916",
  "0917",
]);

const NYSC_CALLUP_NUMBER_RE = /^NYSC\/[A-Z]{3}\/\d{4}\/\d{4,6}$/;
const NYSC_STATE_CODE_RE = /^NYSC\/[A-Z]{2}\/\d{2}[A-C]\/\d{5,6}$/;
const UNIVERSITY_MATRICULATION_NUMBER_RE = /^[A-Z0-9/]{8,16}$/;

type ValidationResult = {
  normalizedValue: string;
  error: string | null;
};

export function normalizeMobileNumber(value: string) {
  return value.trim().replace(/[\s-]+/g, "");
}

export function normalizeNigerianMobileForDisplay(value: string) {
  const normalizedValue = normalizeMobileNumber(value);
  if (!normalizedValue) {
    return "";
  }
  if (normalizedValue.startsWith("+234")) {
    return normalizedValue;
  }
  if (/^0\d{10}$/.test(normalizedValue)) {
    return `+234${normalizedValue.slice(1)}`;
  }
  return normalizedValue;
}

export function normalizeNigerianMobileInput(value: string) {
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

export function validateNigerianMobileNumber(
  value: string,
  label = "Mobile number",
  required = true,
  requireInternationalFormat = false
): ValidationResult {
  const normalizedValue = normalizeMobileNumber(value);

  if (!normalizedValue) {
    return {
      normalizedValue,
      error: required ? `${label} is required.` : null,
    };
  }

  let localNumber = normalizedValue;
  if (normalizedValue.startsWith("+")) {
    if (!/^\+\d+$/.test(normalizedValue)) {
      return {
        normalizedValue,
        error: `Enter a valid ${label.toLowerCase()} using only digits and an optional leading +.`,
      };
    }
    if (!normalizedValue.startsWith("+234")) {
      return {
        normalizedValue,
        error: `Enter a valid Nigerian ${label.toLowerCase()} starting with +234.`,
      };
    }
    if (normalizedValue.length !== 14) {
      return {
        normalizedValue,
        error: "Numbers starting with +234 must contain 13 digits excluding the +.",
      };
    }
    localNumber = `0${normalizedValue.slice(4)}`;
  } else {
    if (requireInternationalFormat) {
      return {
        normalizedValue,
        error: `Enter a valid Nigerian ${label.toLowerCase()} starting with +234.`,
      };
    }
    if (!/^\d+$/.test(normalizedValue)) {
      return {
        normalizedValue,
        error: `Enter a valid ${label.toLowerCase()} using digits only.`,
      };
    }
    if (!normalizedValue.startsWith("0")) {
      return {
        normalizedValue,
        error: `Enter a valid Nigerian ${label.toLowerCase()} starting with 0 or +234.`,
      };
    }
    if (normalizedValue.length !== 11) {
      return {
        normalizedValue,
        error: "Numbers starting with 0 must contain 11 digits.",
      };
    }
  }

  if (![...NIGERIAN_MOBILE_PREFIXES].some((prefix) => localNumber.startsWith(prefix))) {
    return {
      normalizedValue,
      error: "Enter a valid Nigerian mobile number with a supported network prefix.",
    };
  }

  return {
    normalizedValue,
    error: null,
  };
}

export function normalizeNinNumber(value: string) {
  return value.trim().replace(/\s+/g, "");
}

export function validateNinNumber(value: string): ValidationResult {
  const normalizedValue = normalizeNinNumber(value);
  if (!normalizedValue) {
    return {
      normalizedValue,
      error: "NIN Number is required.",
    };
  }
  if (!/^\d{11}$/.test(normalizedValue)) {
    return {
      normalizedValue,
      error: "NIN Number must be exactly 11 digits.",
    };
  }
  return {
    normalizedValue,
    error: null,
  };
}

export function normalizeNyscCallupNumber(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

export function validateNyscCallupNumber(value: string): ValidationResult {
  const normalizedValue = normalizeNyscCallupNumber(value);
  if (!normalizedValue) {
    return {
      normalizedValue,
      error: "NYSC Call-up Number is required.",
    };
  }
  if (!NYSC_CALLUP_NUMBER_RE.test(normalizedValue)) {
    return {
      normalizedValue,
      error: "NYSC Call-up Number must match the format NYSC/ABC/2024/1234.",
    };
  }
  return {
    normalizedValue,
    error: null,
  };
}

export function normalizeNyscStateCode(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

export function validateNyscStateCode(value: string): ValidationResult {
  const normalizedValue = normalizeNyscStateCode(value);
  if (!normalizedValue) {
    return {
      normalizedValue,
      error: "NYSC State Code is required.",
    };
  }
  if (!NYSC_STATE_CODE_RE.test(normalizedValue)) {
    return {
      normalizedValue,
      error: "NYSC State Code must match the format NYSC/LG/26B/72673.",
    };
  }

  return {
    normalizedValue,
    error: null,
  };
}

export function normalizeUniversityMatriculationNumber(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}

export function validateUniversityMatriculationNumber(value: string): ValidationResult {
  const normalizedValue = normalizeUniversityMatriculationNumber(value);
  if (!normalizedValue) {
    return {
      normalizedValue,
      error: "University Matriculation Number is required.",
    };
  }
  if (!UNIVERSITY_MATRICULATION_NUMBER_RE.test(normalizedValue)) {
    return {
      normalizedValue,
      error: 'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".',
    };
  }
  return {
    normalizedValue,
    error: null,
  };
}
