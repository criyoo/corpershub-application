import { useCallback, useEffect, useRef, useState } from "react";

export type InactivityState = {
  remainingSeconds: number;
  isWarning: boolean;
  extendSession: () => void;
  logoutNow: () => void;
  stop: () => void;
};

export type InactivityOptions = {
  onWarning?: () => void;
  onLogout?: () => void;
  warningMinutes?: number;
  logoutMinutes?: number;
  enabled?: boolean;
};

export function useInactivityTimeout(
  {
    onWarning,
    onLogout,
    warningMinutes = 25,
    logoutMinutes = 30,
    enabled = true,
  }: InactivityOptions = {}
): InactivityState {
  const initialSeconds = enabled ? logoutMinutes * 60 : 0;
  const [remainingSeconds, setRemainingSeconds] = useState(initialSeconds);
  const [isWarning, setIsWarning] = useState(false);
  const timerRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);
  const remainingRef = useRef(initialSeconds);
  const warningTriggeredRef = useRef(false);
  const warningSeconds = warningMinutes * 60;
  const logoutSeconds = logoutMinutes * 60;

  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      globalThis.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clearTimers();
    setRemainingSeconds(0);
    setIsWarning(false);
    warningTriggeredRef.current = false;
  }, [clearTimers]);

  const logoutNow = useCallback(() => {
    stop();
    onLogout?.();
  }, [stop, onLogout]);

  const extendSession = useCallback(() => {
    remainingRef.current = logoutSeconds;
    setRemainingSeconds(logoutSeconds);
    setIsWarning(false);
    warningTriggeredRef.current = false;
  }, [logoutSeconds]);

  useEffect(() => {
    if (!enabled) {
      stop();
      return;
    }

    remainingRef.current = logoutSeconds;
    setRemainingSeconds(logoutSeconds);
    setIsWarning(false);
    warningTriggeredRef.current = false;

    const activityEvents: Array<keyof WindowEventMap> = [
      "mousedown",
      "mousemove",
      "keydown",
      "scroll",
      "touchstart",
      "click",
    ];

    const handleActivity = () => {
      extendSession();
    };

    activityEvents.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    timerRef.current = globalThis.setInterval(() => {
      remainingRef.current -= 1;
      const current = remainingRef.current;
      setRemainingSeconds(current);

      if (!warningTriggeredRef.current && current <= warningSeconds) {
        warningTriggeredRef.current = true;
        setIsWarning(true);
        onWarning?.();
      }

      if (current <= 0) {
        logoutNow();
      }
    }, 1000);

    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      clearTimers();
    };
  }, [enabled, extendSession, logoutNow, clearTimers, warningSeconds, onWarning, logoutSeconds, stop]);

  return { remainingSeconds, isWarning, extendSession, logoutNow, stop };
}
