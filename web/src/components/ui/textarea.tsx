import clsx from "clsx";
import { forwardRef, type TextareaHTMLAttributes } from "react";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  hasError?: boolean;
};

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, hasError, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={clsx(
          "min-h-28 w-full rounded-2xl border bg-white/[0.05] px-4 py-3 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md placeholder:text-white/45 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:border-white/8 disabled:bg-white/[0.035] disabled:text-slate-400",
          hasError
            ? "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50"
            : "border-white/10 focus:border-white/20 focus:ring-lime/25",
          className
        )}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";
