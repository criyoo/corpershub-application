"use client";

import Link from "next/link";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { useApiQuery } from "@/hooks/use-api-query";
import { Card } from "@/components/ui/card";

type Overview = {
  total_users: number;
  total_companies: number;
  total_corpers: number;
  total_interests: number;
  total_conversations: number;
  successful_payments: number;
  pending_admin_requests: number;
};

const quickActions = [
  {
    href: "/admin/access-requests",
    label: "Admin access",
    description: "Approve or reject pending admin registration requests.",
  },
  {
    href: "/admin/corper-verifications",
    label: "Corper verifications",
    description: "Review NIN, call-up, state code, and biodata checks.",
  },
  {
    href: "/admin/companies",
    label: "Company reviews",
    description: "Approve company profiles and registration details.",
  },
  {
    href: "/admin/users",
    label: "User accounts",
    description: "Inspect account status, roles, and access.",
  },
  {
    href: "/admin/payments",
    label: "Payments",
    description: "Monitor subscription transactions and outcomes.",
  },
  {
    href: "/admin/configuration",
    label: "Configuration",
    description: "Manage platform options and email domain rules.",
  },
  {
    href: "/admin/audit",
    label: "Audit log",
    description: "Track administrative and system activity.",
  },
];

export default function AdminOverviewPage() {
  const { data } = useApiQuery<Overview>("/adminpanel/overview/");
  const successfulPayments = data?.successful_payments ?? 0;
  const pendingAdminRequests = data?.pending_admin_requests ?? 0;
  const totalUsers = data?.total_users ?? 0;
  const totalProfiles = (data?.total_companies ?? 0) + (data?.total_corpers ?? 0);

  return (
    <DashboardShell
      role="admin"
      title="Admin Dashboard"
      headerAside={<span className="text-sm text-mist">Secure application management</span>}
    >
      <div className="grid gap-6">
        <section className="overflow-hidden rounded-[28px] border border-lime/20 bg-[linear-gradient(135deg,rgba(31,183,102,0.2),rgba(255,255,255,0.08))] p-6">
          <div className="grid gap-5 lg:grid-cols-[1.4fr_0.8fr] lg:items-end">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-lime">corpershub control center</p>
              <h2 className="mt-3 font-display text-3xl text-white">Manage verification, users, payments, and platform health.</h2>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-mist">
                Use this workspace to keep the marketplace clean, review onboarding records, monitor conversations and interests, and keep subscription activity visible.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.08] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-lime">Profiles</p>
                <p className="mt-2 font-display text-3xl text-white">{totalProfiles}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.08] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-lime">Users</p>
                <p className="mt-2 font-display text-3xl text-white">{totalUsers}</p>
              </div>
            </div>
          </div>
        </section>

        <StatsGrid
          items={[
            { label: "Total users", value: totalUsers },
            { label: "Companies", value: data?.total_companies ?? 0 },
            { label: "Corpers", value: data?.total_corpers ?? 0 },
            { label: "Interests", value: data?.total_interests ?? 0 },
            { label: "Conversations", value: data?.total_conversations ?? 0 },
            { label: "Successful payments", value: successfulPayments },
            { label: "Pending admin requests", value: pendingAdminRequests }
          ]}
        />

        <section>
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-lime">Admin navigation</p>
              <h2 className="mt-2 font-display text-2xl text-white">Quick actions</h2>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {quickActions.map((action) => (
              <Link key={action.href} href={action.href} className="group">
                <Card className="h-full transition duration-200 group-hover:border-lime/50 group-hover:bg-white/[0.09]">
                  <div className="flex h-full flex-col justify-between gap-6">
                    <div>
                      <p className="font-display text-xl text-white">{action.label}</p>
                      <p className="mt-3 text-sm leading-6 text-mist">{action.description}</p>
                    </div>
                    <span className="inline-flex w-fit rounded-full border border-lime/30 bg-lime/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-lime">
                      Open
                    </span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <Card>
            <p className="text-xs uppercase tracking-[0.24em] text-lime">Operations</p>
            <h2 className="mt-3 font-display text-2xl text-white">Verification workflow</h2>
            <p className="mt-3 text-sm leading-6 text-mist">
              Start with corper and company verification queues. Approved records unlock discovery, matching, and deeper platform activity.
            </p>
          </Card>
          <Card>
            <p className="text-xs uppercase tracking-[0.24em] text-lime">Billing</p>
            <h2 className="mt-3 font-display text-2xl text-white">Subscription monitoring</h2>
            <p className="mt-3 text-sm leading-6 text-mist">
              Use payments and subscriptions to review active plans, transaction outcomes, and billing-related support issues.
            </p>
          </Card>
        </section>
      </div>
    </DashboardShell>
  );
}
