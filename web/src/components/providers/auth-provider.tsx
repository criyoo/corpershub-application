"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { restoreSessionFromRefreshCookie } from "@/lib/api";
import { clearSession, getSession, setSession, type SessionState } from "@/lib/session";

type AuthContextValue = {
  session: SessionState | null;
  hydrated: boolean;
  updateSession: (value: SessionState | null) => void;
  logout: () => void;
  extendSession: () => void;
  inactivityWarning: boolean;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function sessionsEqual(left: SessionState | null, right: SessionState | null) {
  if (left === right) {
    return true;
  }

  try {
    return JSON.stringify(left) === JSON.stringify(right);
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setCurrentSession] = useState<SessionState | null>(null);
  const sessionRef = useRef<SessionState | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [inactivityWarning, setInactivityWarning] = useState(false);

  const updateSession = useCallback((value: SessionState | null) => {
    if (sessionsEqual(sessionRef.current, value)) {
      return;
    }
    sessionRef.current = value;
    setCurrentSession(value);
    if (value) {
      setSession(value);
    } else {
      clearSession();
    }
  }, []);

  const logout = useCallback(() => {
    sessionRef.current = null;
    setCurrentSession(null);
    clearSession();
    window.location.replace("/");
  }, []);

  const extendSession = useCallback(() => {
    setInactivityWarning(false);
  }, []);

  useEffect(() => {
    const existingSession = getSession();
    if (existingSession) {
      sessionRef.current = existingSession;
      setCurrentSession(existingSession);
      setHydrated(true);
      return;
    }

    void restoreSessionFromRefreshCookie()
      .then((restoredSession) => {
        sessionRef.current = restoredSession;
        setCurrentSession(restoredSession);
      })
      .finally(() => {
        setHydrated(true);
      });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      hydrated,
      updateSession,
      logout,
      extendSession,
      inactivityWarning,
    }),
    [session, hydrated, updateSession, logout, extendSession, inactivityWarning]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
