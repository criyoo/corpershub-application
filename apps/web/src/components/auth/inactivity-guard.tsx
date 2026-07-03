"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { useInactivityTimeout } from "@/hooks/use-inactivity-timeout";
import { InactivityWarningModal } from "@/components/auth/inactivity-warning-modal";
import { useCallback } from "react";

export function InactivityGuard() {
  const { session, logout, extendSession } = useAuth();

  const onWarning = useCallback(() => {
    if (session) {
      extendSession();
    }
  }, [session, extendSession]);

  const onLogout = useCallback(() => {
    logout();
  }, [logout]);

  const { remainingSeconds, isWarning, extendSession: extendInactivity, logoutNow } = useInactivityTimeout({
    enabled: Boolean(session),
    warningMinutes: 25,
    logoutMinutes: 30,
    onWarning,
    onLogout: session ? onLogout : undefined,
  });

  const handleExtend = useCallback(() => {
    extendInactivity();
    extendSession();
  }, [extendInactivity, extendSession]);

  return (
    <InactivityWarningModal
      open={isWarning}
      onExtend={handleExtend}
      onLogout={logoutNow}
      remainingSeconds={remainingSeconds}
    />
  );
}
