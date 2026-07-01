import { resolveMediaUrl } from "@/lib/media";

type ConversationCounterpartProps = {
  name: string;
  image?: string | null;
  meta?: string;
  fallbackLabel: string;
};

function getInitials(value: string) {
  const words = value
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (words.length === 0) {
    return "NA";
  }

  return words.map((word) => word[0]?.toUpperCase() ?? "").join("");
}

export function ConversationCounterpart({
  name,
  image,
  meta,
  fallbackLabel,
}: ConversationCounterpartProps) {
  const displayName = name.trim() || fallbackLabel;
  const imageUrl = resolveMediaUrl(image);

  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="h-11 w-11 shrink-0 overflow-hidden rounded-full border border-white/10 bg-white/10 shadow-[0_8px_24px_rgba(4,21,15,0.12)]">
        {imageUrl ? (
          <img src={imageUrl} alt={displayName} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-[#0F5A3A]/70 text-xs font-semibold uppercase tracking-[0.14em] text-white">
            {getInitials(displayName)}
          </div>
        )}
      </div>
      <div className="min-w-0">
        <p className="truncate text-xs font-semibold text-white">{displayName}</p>
        {meta ? <p className="mt-1 truncate text-xs text-mist">{meta}</p> : null}
      </div>
    </div>
  );
}
