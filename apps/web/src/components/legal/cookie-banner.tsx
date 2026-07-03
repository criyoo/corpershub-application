"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

type CookiePreferences = {
  necessary: true;
  functional: boolean;
  analytics: boolean;
  marketing: boolean;
};

const STORAGE_KEY = "corpershub.cookie-preferences";

const DEFAULT_PREFERENCES: CookiePreferences = {
  necessary: true,
  functional: false,
  analytics: false,
  marketing: false,
};

function persistPreferences(preferences: CookiePreferences) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
}

export function CookieBanner() {
  const [visible, setVisible] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [preferences, setPreferences] = useState<CookiePreferences>(DEFAULT_PREFERENCES);

  useEffect(() => {
    const storedValue = window.localStorage.getItem(STORAGE_KEY);
    if (!storedValue) {
      setVisible(true);
      return;
    }

    try {
      setPreferences(JSON.parse(storedValue) as CookiePreferences);
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
      setVisible(true);
    }
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-4 sm:p-6">
      <div className="mx-auto grid max-w-5xl gap-4 rounded-[28px] border border-white/10 bg-[#0B1D15]/95 p-5 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-xl">
        <div className="grid gap-2">
          <p className="text-sm leading-7 text-white/82">
            We use cookies to improve security, remember your preferences, and enhance your
            experience. By continuing to use corpershub, you consent to our use of cookies in
            accordance with our{" "}
            <Link href="/legal/cookies-policy" className="font-semibold text-lime hover:text-white">
              Cookies Policy
            </Link>
            .
          </p>
        </div>

        {showPreferences ? (
          <div className="grid gap-3 rounded-[24px] border border-white/10 bg-white/[0.04] p-4 text-sm text-mist sm:grid-cols-2">
            <label className="grid gap-1">
              <span className="font-semibold text-white">Strictly Necessary Cookies (Always Active)</span>
              <span>Required for security, login sessions, and core platform functions.</span>
              <input type="checkbox" checked disabled className="h-4 w-4 accent-[#1FB766]" />
            </label>
            <label className="grid gap-1">
              <span className="font-semibold text-white">Functional Cookies</span>
              <span>Remember interface and preference settings.</span>
              <input
                type="checkbox"
                checked={preferences.functional}
                onChange={(event) =>
                  setPreferences((current) => ({ ...current, functional: event.target.checked }))
                }
                className="h-4 w-4 accent-[#1FB766]"
              />
            </label>
            <label className="grid gap-1">
              <span className="font-semibold text-white">Analytics Cookies</span>
              <span>Help us understand usage and improve the platform.</span>
              <input
                type="checkbox"
                checked={preferences.analytics}
                onChange={(event) =>
                  setPreferences((current) => ({ ...current, analytics: event.target.checked }))
                }
                className="h-4 w-4 accent-[#1FB766]"
              />
            </label>
            <label className="grid gap-1">
              <span className="font-semibold text-white">Marketing Cookies</span>
              <span>Support marketing attribution and campaign measurement.</span>
              <input
                type="checkbox"
                checked={preferences.marketing}
                onChange={(event) =>
                  setPreferences((current) => ({ ...current, marketing: event.target.checked }))
                }
                className="h-4 w-4 accent-[#1FB766]"
              />
            </label>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <Button
            type="button"
            onClick={() => {
              const nextPreferences = {
                necessary: true,
                functional: true,
                analytics: true,
                marketing: true,
              } satisfies CookiePreferences;
              setPreferences(nextPreferences);
              persistPreferences(nextPreferences);
              setVisible(false);
            }}
          >
            Accept All
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              persistPreferences(DEFAULT_PREFERENCES);
              setPreferences(DEFAULT_PREFERENCES);
              setVisible(false);
            }}
          >
            Reject Non-Essential
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              if (showPreferences) {
                persistPreferences(preferences);
              }
              setShowPreferences((current) => !current);
              if (showPreferences) {
                setVisible(false);
              }
            }}
          >
            Manage Preferences
          </Button>
        </div>
      </div>
    </div>
  );
}
