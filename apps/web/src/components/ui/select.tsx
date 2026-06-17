import clsx from "clsx";
import type { CSSProperties, SelectHTMLAttributes } from "react";

const placeholderSelectStyle: CSSProperties = {
  color: "rgba(255, 255, 255, 0.45)",
  fontSize: "0.875rem",
};

function isEmptySelectValue(value: SelectHTMLAttributes<HTMLSelectElement>["value"]) {
  return value === "" || (Array.isArray(value) && value.length === 0);
}

export function Select({ className, style, value, defaultValue, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  const hasEmptySelectedValue =
    isEmptySelectValue(value) || (value === undefined && isEmptySelectValue(defaultValue));

  return (
    <select
      className={clsx(
        "w-full rounded-2xl border border-white/10 bg-transparent px-4 py-3 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-lime/25 disabled:cursor-not-allowed disabled:border-white/8 disabled:bg-transparent disabled:text-slate-400 [&_optgroup]:bg-transparent [&_optgroup]:text-sm [&_optgroup]:text-[grey] [&_option]:bg-transparent [&_option]:text-sm [&_option]:text-[grey]",
        className
      )}
      style={hasEmptySelectedValue ? { ...placeholderSelectStyle, ...style } : style}
      value={value}
      defaultValue={defaultValue}
      {...props}
    />
  );
}
