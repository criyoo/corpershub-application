"use client";

import { Eye, EyeOff } from "lucide-react";
import clsx from "clsx";
import { useState, type InputHTMLAttributes } from "react";

const baseInputClassName =
  "w-full rounded-2xl border bg-white/[0.05] px-4 py-3 text-sm text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-md placeholder:text-white/45 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:border-white/8 disabled:bg-white/[0.035] disabled:text-slate-400";

const borderClassName = "border-white/10 focus:border-white/20 focus:ring-lime/25";
const errorBorderClassName = "border-2 border-red-500 ring-2 ring-red-500/45 focus:border-red-500 focus:ring-red-500/50";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  hasError?: boolean;
};

export function Input({
  className,
  disabled,
  type,
  hasError,
  ...props
}: InputProps) {
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const isPasswordField = type === "password";
  const resolvedType = isPasswordField && isPasswordVisible ? "text" : type;

  const inputClass = clsx(
    baseInputClassName,
    hasError ? errorBorderClassName : borderClassName,
    className
  );

  if (!isPasswordField) {
    return (
      <input
        className={inputClass}
        disabled={disabled}
        type={type}
        {...props}
      />
    );
  }

  return (
    <div className="relative">
      <input
        className={clsx(inputClass, "pr-12")}
        disabled={disabled}
        type={resolvedType}
        {...props}
      />
      <button
        type="button"
        aria-label={isPasswordVisible ? "Hide password" : "Show password"}
        aria-pressed={isPasswordVisible}
        className="absolute right-3 top-1/2 inline-flex -translate-y-1/2 items-center justify-center text-slate-400 transition hover:text-white focus:outline-none focus:ring-2 focus:ring-lime/25 disabled:cursor-not-allowed disabled:text-slate-500"
        disabled={disabled}
        onClick={() => setIsPasswordVisible((current) => !current)}
      >
        {isPasswordVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}
