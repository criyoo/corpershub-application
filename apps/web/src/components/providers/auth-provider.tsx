"use client";

import { createContext, useContext, useEffect, useState } from "react";

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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setCurrentSession] = useState<SessionState | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [inactivityWarning, setInactivityWarning] = useState(false);

  const updateSession = (value: SessionState | null) => {
    setCurrentSession(value);
    if (value) {
      setSession(value);
    } else {
      clearSession();
    }
  };

  const logout = () => {
    updateSession(null);
    window.location.replace("/");
  };

  const extendSession = () => {
    setInactivityWarning(false);
  };

  const triggerWarning = () => {
    if (session) {
      setInactivityWarning(true);
    }
  };

  const triggerLogout = () => {
    if (session) {
      logout();
    }
  };

  useEffect(() => {
    const existingSession = getSession();
    if (existingSession) {
      setCurrentSession(existingSession);
      setHydrated(true);
      return;
    }

    void restoreSessionFromRefreshCookie()
      .then((restoredSession) => {
        setCurrentSession(restoredSession);
      })
      .finally(() => {
        setHydrated(true);
      });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        session,
        hydrated,
        updateSession,
        logout,
        extendSession,
        inactivityWarning,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
