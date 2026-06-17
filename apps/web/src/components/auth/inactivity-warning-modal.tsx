"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

type InactivityWarningModalProps = {
  open: boolean;
  onExtend: () => void;
  onLogout: () => void;
  remainingSeconds: number;
};

function formatCountdown(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

export function InactivityWarningModal({
  open,
  onExtend,
  onLogout,
  remainingSeconds,
}: InactivityWarningModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-ink/95 p-8 shadow-glow">
        <h2 className="font-display text-2xl text-white">Are you still there?</h2>
        <p className="mt-3 text-sm text-mist">
          You will be automatically logged out in {formatCountdown(remainingSeconds)} due to inactivity.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button variant="secondary" type="button" onClick={onLogout}>
            Log out now
          </Button>
          <Button type="button" onClick={onExtend}>
            Keep me signed in
          </Button>
        </div>
      </div>
    </div>
  );
}
