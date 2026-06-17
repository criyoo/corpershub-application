import clsx from "clsx";
import { forwardRef, type TextareaHTMLAttributes } from "react";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={clsx(
          "min-h-28 w-full rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md placeholder:text-white/45 focus:border-white/20 focus:outline-none focus:ring-2 focus:ring-lime/25 disabled:cursor-not-allowed disabled:border-white/8 disabled:bg-white/[0.035] disabled:text-slate-400",
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";
