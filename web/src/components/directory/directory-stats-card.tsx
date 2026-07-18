type DirectoryStatItem = {
  label: string;
  value: number;
};

function getLabelLines(label: string) {
  const words = label.trim().split(/\s+/).filter(Boolean);
  if (words.length <= 1) {
    return [words[0] ?? "", ""];
  }

  const midpoint = Math.ceil(words.length / 2);
  return [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")];
}

export function DirectoryStatsCard({
  title = "Visible now",
  items,
}: {
  title?: string;
  items: DirectoryStatItem[];
}) {
  return (
    <div className="w-full max-w-[420px] rounded-[28px] border border-white/10 bg-[#07140E]/45 px-4 py-4 sm:px-5 sm:py-5">
      <p className="text-xs uppercase tracking-[0.22em] text-lime">{title}</p>
      <div className="mt-4 grid grid-cols-3 divide-x divide-white/10 overflow-hidden rounded-[22px] border border-white/20 bg-white/[0.04]">
        {items.map((item) => {
          const [firstLine, secondLine] = getLabelLines(item.label);

          return (
          <div key={item.label} className="grid min-h-[104px] grid-rows-[2.7rem_auto] px-2 py-4 text-center sm:px-3">
            <p className="flex flex-col items-center justify-center text-[8.5px] uppercase leading-4 tracking-[0.12em] text-lime sm:text-[10px]">
              <span>{firstLine}</span>
              <span>{secondLine || "\u00A0"}</span>
            </p>
            <p className="self-start font-display text-xl text-white sm:text-2xl">
              {item.value.toLocaleString()}
            </p>
          </div>
          );
        })}
      </div>
    </div>
  );
}
