import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition duration-200 focus:outline-none focus:ring-2 focus:ring-lime focus:ring-offset-2 focus:ring-offset-ink disabled:cursor-not-allowed disabled:opacity-60",
        {
          "bg-[linear-gradient(135deg,#1FB766_0%,#118A48_100%)] text-[#E6D28C] shadow-[0_18px_35px_rgba(17,138,72,0.28)] hover:brightness-105": variant === "primary",
          "border border-white/15 bg-white/[0.08] text-white hover:border-lime/70 hover:bg-white/[0.14]": variant === "secondary",
          "text-mist hover:bg-white/[0.06] hover:text-white": variant === "ghost",
          "bg-coral text-white hover:bg-[#bf4545]": variant === "danger"
        },
        className
      )}
      {...props}
    />
  );
}
