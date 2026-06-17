import type { ComponentType, SVGProps } from "react";

import type { UserRole } from "@/lib/session";

type NavIconProps = SVGProps<SVGSVGElement>;

function OverviewIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" stroke="#7CD9A1" fill="#7CD9A122" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" stroke="#38BDF8" fill="#38BDF822" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="#F97316" fill="#F9731622" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" stroke="#FACC15" fill="#FACC1522" />
    </svg>
  );
}

function ProfileIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#38BDF8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="8" r="4" fill="#38BDF822" />
      <path d="M5 20c1.8-3.4 4.2-5 7-5s5.2 1.6 7 5" />
    </svg>
  );
}

function VerificationIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#FACC15" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3l7 3v6c0 4.4-2.7 7.7-7 9-4.3-1.3-7-4.6-7-9V6l7-3z" fill="#FACC151F" />
      <path d="m9.5 12 1.8 1.8 3.7-4" />
    </svg>
  );
}

function CompaniesIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#FB7185" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 21V7l4-4h8l4 4v14" fill="#FB718514" />
      <path d="M9 21v-5h6v5" />
      <path d="M9 8h.01" />
      <path d="M15 8h.01" />
      <path d="M9 12h.01" />
      <path d="M15 12h.01" />
    </svg>
  );
}

function InterestsIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#F97316" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z" fill="#F9731622" />
    </svg>
  );
}

function NotificationsIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#A78BFA" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M6 9a6 6 0 1 1 12 0c0 6 2 7 2 7H4s2-1 2-7" fill="#A78BFA1D" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </svg>
  );
}

function ChatIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#22D3EE" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M6 18H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-8l-4 3v-3z" fill="#22D3EE1D" />
      <path d="M8 10h8" />
      <path d="M8 14h5" />
    </svg>
  );
}

function BillingIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#60A5FA" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="3" y="5" width="18" height="14" rx="2" fill="#60A5FA1A" />
      <path d="M3 10h18" />
      <path d="M7 15h3" />
      <path d="M13 15h4" />
    </svg>
  );
}

function SettingsIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="3" fill="#34D39922" />
      <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 0 1 0 2.8 2 2 0 0 1-2.8 0l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.2a1 1 0 0 0-.6-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 0 1-2.8 0 2 2 0 0 1 0-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.2a1 1 0 0 0 .9-.6 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 0 1 0-2.8 2 2 0 0 1 2.8 0l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.2a1 1 0 0 0 .6.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 0 1 2.8 0 2 2 0 0 1 0 2.8l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.2a1 1 0 0 0-.9.6z" />
    </svg>
  );
}

function SupportIcon(props: NavIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="#F4D35E" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 18h.01" />
      <path d="M9.2 9a2.8 2.8 0 1 1 4.9 1.8c-.7.8-1.5 1.3-2.1 1.9-.4.4-.6.8-.6 1.6" />
      <path d="M4 12a8 8 0 1 0 16 0 8 8 0 1 0-16 0" fill="#F4D35E1A" />
    </svg>
  );
}

export type NavItem = {
  href: string;
  label: string;
  icon?: ComponentType<NavIconProps>;
  section?: string;
};

export const dashboardNav: Record<UserRole, NavItem[]> = {
  company: [
    { href: "/company/dashboard", label: "Overview", icon: OverviewIcon },
    { href: "/about", label: "About", icon: SupportIcon },
    { href: "/how-it-works", label: "How It Works", icon: SupportIcon },
    { href: "/company/verification", label: "Verification", icon: VerificationIcon },
    { href: "/company/profile", label: "Profile", icon: ProfileIcon },
    { href: "/company/corpers", label: "Discover Corpers", icon: CompaniesIcon },
    { href: "/company/notifications", label: "Corpers Interested", icon: NotificationsIcon },
    { href: "/company/faq", label: "FAQ", icon: SupportIcon },
    { href: "/company/interests", label: "My Interest", icon: InterestsIcon },
    { href: "/company/chat", label: "Chat", icon: ChatIcon },
    { href: "/company/settings", label: "Settings", icon: SettingsIcon },
    { href: "/company/support", label: "Support", icon: SupportIcon },
  ],
  corper: [
    { href: "/corper/dashboard", label: "Overview", icon: OverviewIcon },
    { href: "/about", label: "About", icon: SupportIcon },
    { href: "/how-it-works", label: "How It Works", icon: SupportIcon },
    { href: "/corper/profile", label: "Profile", icon: ProfileIcon },
    { href: "/corper/companies", label: "Discover Companies", icon: CompaniesIcon },
    { href: "/corper/notifications", label: "Companies Interested", icon: NotificationsIcon },
    { href: "/corper/faq", label: "FAQ", icon: SupportIcon },
    { href: "/corper/interests", label: "My Interests", icon: InterestsIcon },
    { href: "/corper/chat", label: "Chat", icon: ChatIcon },
    { href: "/corper/verification", label: "Verification", icon: VerificationIcon },
    { href: "/corper/billing", label: "Billing", icon: BillingIcon },
    { href: "/corper/settings", label: "Settings", icon: SettingsIcon },
    { href: "/corper/support", label: "Support", icon: SupportIcon },
  ],
  admin: [
    { href: "/admin/overview", label: "Overview", section: "Workspace" },
    { href: "/admin/users", label: "Users", section: "Accounts" },
    { href: "/admin/access-requests", label: "Admin Requests", section: "Accounts" },
    { href: "/admin/companies", label: "Companies", section: "Accounts" },
    { href: "/admin/corpers", label: "Corpers", section: "Accounts" },
    { href: "/admin/companies-verifications", label: "Company Verifications", section: "Verifications" },
    { href: "/admin/corper-verifications", label: "Corper Verifications", section: "Verifications" },
    { href: "/admin/verifications", label: "Verification Attempts", section: "Verifications" },
    { href: "/admin/subscriptions", label: "Subscriptions", section: "Billing" },
    { href: "/admin/payments", label: "Payments", section: "Billing" },
    { href: "/admin/audit", label: "Audit", section: "Platform" },
    { href: "/admin/configuration", label: "Configuration", section: "Platform" }
  ]
};
