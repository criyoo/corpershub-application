import type { Metadata } from "next";
import { Toaster } from "sonner";

import { CookieBanner } from "@/components/legal/cookie-banner";
import { GlobalAuthMenu } from "@/components/layout/global-auth-menu";
import { GlobalPublicFooter } from "@/components/layout/global-public-footer";
import { AuthProvider } from "@/components/providers/auth-provider";
import { CorperVerificationDraftProvider } from "@/components/providers/corper-verification-draft-provider";
import { InactivityGuard } from "@/components/auth/inactivity-guard";

import "./globals.css";

export const metadata: Metadata = {
  title: "corpershub",
  description: "Find trusted NYSC opportunities and manage placements with confidence."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://c.superprof.com" crossOrigin="anonymous" />
      </head>
      <body>
        <AuthProvider>
          <CorperVerificationDraftProvider>
            <InactivityGuard />
            <GlobalAuthMenu />
            {children}
            <GlobalPublicFooter />
            <CookieBanner />
            <Toaster richColors position="top-right" />
          </CorperVerificationDraftProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
