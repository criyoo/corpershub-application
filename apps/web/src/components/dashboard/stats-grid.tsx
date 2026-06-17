import { Card } from "@/components/ui/card";

export function StatsGrid({
  items,
  columns = "four"
}: {
  items: { label: string; value: string | number; caption?: string; span?: "full" }[];
  columns?: "two" | "four";
}) {
  const gridClass = columns === "two" ? "grid gap-4 md:grid-cols-2" : "grid gap-4 md:grid-cols-2 xl:grid-cols-4";

  return (
    <div className={gridClass}>
      {items.map((item) => (
        <Card key={item.label} className={item.span === "full" ? "md:col-span-2" : undefined}>
          <p className="text-sm text-mist">{item.label}</p>
          <h3 className="mt-3 font-display text-3xl text-white">{item.value}</h3>
          {item.caption ? <p className="mt-2 text-xs text-mist">{item.caption}</p> : null}
        </Card>
      ))}
    </div>
  );
}
