export function formatVerificationType(type: string) {
  switch (type.toLowerCase()) {
    case "biodata":
      return "BIODATA";
    case "nin":
      return "NIN";
    case "callup":
      return "NYSC CALL-UP";
    case "state_code":
      return "NYSC STATE CODE";
    case "profile":
      return "PROFILE";
    default:
      return type.replaceAll("_", " ").toUpperCase();
  }
}

export function formatVerificationStatus(status: string) {
  switch (status.toLowerCase()) {
    case "unsubmitted":
      return "Unsubmitted";
    case "under_review":
      return "Under Review";
    default:
      return status
        .replaceAll("_", " ")
        .split(" ")
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
        .join(" ");
  }
}
