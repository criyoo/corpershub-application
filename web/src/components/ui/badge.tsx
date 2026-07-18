import clsx from "clsx";

export function Badge({
  children,
  className,
  tone = "neutral",
}: {
  children: React.ReactNode;
  className?: string;
  tone?: "neutral" | "success" | "warning";
  key?: React.Key;
}) {
  return (
    <span
      className={clsx(
        "inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]",
        {
          "border-white/15 bg-white/[0.06] text-mist": tone === "neutral",
          "border-lime/40 bg-lime/10 text-lime": tone === "success",
          "border-coral/40 bg-coral/10 text-coral": tone === "warning"
        },
        className
      )}
    >
      {children}
    </span>
  );
}
