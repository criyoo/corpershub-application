"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

type BackButtonProps = {
  fallbackHref?: string;
  label?: string;
  useHistory?: boolean;
};

export function BackButton({ fallbackHref = "/", label = "Back", useHistory = true }: BackButtonProps) {
  const router = useRouter();

  function handleBack() {
    if (useHistory && window.history.length > 1) {
      router.back();
      return;
    }

    router.push(fallbackHref);
  }

  return (
    <button
      type="button"
      onClick={handleBack}
      className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.07] px-4 py-2 text-sm text-mist transition hover:border-lime/60 hover:bg-white/[0.12] hover:text-white"
    >
      <ArrowLeft className="h-4 w-4" />
      {label}
    </button>
  );
}
