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
  warningCountdownSeconds?: number;
  logoutMinutes?: number;
  enabled?: boolean;
};

export function useInactivityTimeout(
  {
    onWarning,
    onLogout,
    warningMinutes = 25,
    warningCountdownSeconds = 120,
    logoutMinutes = 30,
    enabled = true,
  }: InactivityOptions = {}
): InactivityState {
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [isWarning, setIsWarning] = useState(false);
  const timerRef = useRef<ReturnType<typeof globalThis.setInterval> | null>(null);
  const mainRemainingRef = useRef(0);
  const warningRemainingRef = useRef(0);
  const warningTriggeredRef = useRef(false);

  const onWarningRef = useRef(onWarning);
  onWarningRef.current = onWarning;
  const onLogoutRef = useRef(onLogout);
  onLogoutRef.current = onLogout;
  const logoutSecondsRef = useRef(logoutMinutes * 60);

  const warningSeconds = warningMinutes * 60;

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
    onLogoutRef.current?.();
  }, [stop]);

  const extendSession = useCallback(() => {
    mainRemainingRef.current = logoutSecondsRef.current;
    setRemainingSeconds(logoutSecondsRef.current);
    setIsWarning(false);
    warningTriggeredRef.current = false;
  }, []);

  const startWarningCountdown = useCallback(() => {
    setIsWarning(true);
    warningRemainingRef.current = warningCountdownSeconds;
    setRemainingSeconds(warningCountdownSeconds);
    onWarningRef.current?.();
  }, [warningCountdownSeconds]);

  useEffect(() => {
    if (!enabled) {
      stop();
      return;
    }

    mainRemainingRef.current = logoutSecondsRef.current;
    setRemainingSeconds(logoutSecondsRef.current);
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
      // If already in warning state, only reset the countdown but keep the modal open
      if (warningTriggeredRef.current) {
        warningRemainingRef.current = warningCountdownSeconds;
        setRemainingSeconds(warningRemainingRef.current);
        return;
      }
      extendSession();
    };

    activityEvents.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    timerRef.current = globalThis.setInterval(() => {
      if (!warningTriggeredRef.current) {
        mainRemainingRef.current -= 1;

        if (mainRemainingRef.current <= warningSeconds) {
          warningTriggeredRef.current = true;
          startWarningCountdown();
        } else {
          setRemainingSeconds(mainRemainingRef.current);
        }
      } else {
        warningRemainingRef.current -= 1;
        setRemainingSeconds(warningRemainingRef.current);

        if (warningRemainingRef.current <= 0) {
          logoutNow();
        }
      }
    }, 1000);

    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      clearTimers();
    };
  }, [enabled, extendSession, logoutNow, clearTimers, warningSeconds, stop, startWarningCountdown]);

  return { remainingSeconds, isWarning, extendSession, logoutNow, stop };
}