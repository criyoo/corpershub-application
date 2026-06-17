export function resolveMediaUrl(path?: string | null) {
  if (!path) {
    return null;
  }

  const normalized = path.trim();
  if (!normalized) {
    return null;
  }

  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return normalized;
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";
  const origin = apiBaseUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");
  return `${origin}${normalized.startsWith("/") ? normalized : `/${normalized}`}`;
}
