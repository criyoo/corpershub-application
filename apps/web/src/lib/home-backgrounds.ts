const IMAGE_FILE_PATTERN = /^[a-zA-Z0-9._-]+\.(?:jpe?g|png|webp|avif)$/i;

type HomeBackgroundManifest = {
  images?: Array<{
    name?: string;
    url?: string;
  }>;
};

function getApiOrigin() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";
  return apiBaseUrl.replace(/\/api\/?$/, "").replace(/\/$/, "");
}

function buildImageUrl(name: string) {
  return `${getApiOrigin()}/api/home-backgrounds/${encodeURIComponent(name)}`;
}

export function getHomeBackgroundManifestUrl() {
  return process.env.NEXT_PUBLIC_HOME_BACKGROUNDS_MANIFEST_URL ?? `${getApiOrigin()}/api/home-backgrounds/`;
}

export async function fetchHomeBackgroundImageUrls() {
  try {
    const response = await fetch(getHomeBackgroundManifestUrl(), {
      cache: "force-cache"
    });

    if (!response.ok) {
      return [];
    }

    const payload = (await response.json()) as HomeBackgroundManifest;

    return (payload.images ?? [])
      .map((image) => {
        if (typeof image.url === "string" && image.url.trim() !== "") {
          return image.url;
        }

        if (typeof image.name === "string" && IMAGE_FILE_PATTERN.test(image.name)) {
          return buildImageUrl(image.name);
        }

        return null;
      })
      .filter((imageUrl): imageUrl is string => typeof imageUrl === "string");
  } catch {
    return [];
  }
}
