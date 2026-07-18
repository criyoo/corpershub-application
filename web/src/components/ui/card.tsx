import clsx from "clsx";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "rounded-[28px] border border-white/10 bg-white/[0.06] p-6 shadow-glow backdrop-blur-xl",
        className
      )}
      {...props}
    />
  );
}
