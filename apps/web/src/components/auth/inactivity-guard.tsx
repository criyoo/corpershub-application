"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { useInactivityTimeout } from "@/hooks/use-inactivity-timeout";
import { InactivityWarningModal } from "@/components/auth/inactivity-warning-modal";

export function InactivityGuard() {
  const { session, logout, extendSession } = useAuth();

  const { remainingSeconds, isWarning, extendSession: extendInactivity, logoutNow } = useInactivityTimeout({
    enabled: Boolean(session),
    warningMinutes: 25,
    logoutMinutes: 30,
    onWarning: () => {
      if (session) {
        extendSession();
      }
    },
    onLogout: session ? logout : undefined,
  });

  const handleExtend = () => {
    extendInactivity();
    extendSession();
  };

  return (
    <InactivityWarningModal
      open={isWarning}
      onExtend={handleExtend}
      onLogout={logoutNow}
      remainingSeconds={remainingSeconds}
    />
  );
}
