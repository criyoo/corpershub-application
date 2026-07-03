"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import {
  MessageSquare,
  PhoneCall,
  Mail,
  Lightbulb,
  CircleHelp,
  X,
} from "lucide-react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import type { UserRole } from "@/lib/session";
import type { SupportFaqItem } from "@/lib/support-faq";

const SUPPORT_EMAIL = "support@corpershub.ng";
const SUPPORT_PHONE = "+2347047002662";
const SUPPORT_PHONE_DISPLAY = "+234 704 700 2662";

type SupportPageProps = {
  role: Extract<UserRole, "company" | "corper">;
};

type EmailFormState = {
  subject: string;
  message: string;
};

type ImprovementFormState = {
  title: string;
  idea: string;
};

function SupportIconFrame({
  children,
  tone = "lime",
}: {
  children: React.ReactNode;
  tone?: "lime" | "sky" | "amber" | "coral";
}) {
  const toneClass =
    tone === "sky"
      ? "border-sky-300/30 bg-sky-300/10 text-sky-100"
      : tone === "amber"
        ? "border-[#F4D35E]/30 bg-[#F4D35E]/10 text-[#F7E29A]"
        : tone === "coral"
          ? "border-coral/30 bg-coral/10 text-[#F3A3A3]"
          : "border-lime/30 bg-lime/10 text-lime";

  return <div className={`flex h-14 w-14 items-center justify-center rounded-[18px] border ${toneClass}`}>{children}</div>;
}

function buildSupportRoute(role: SupportPageProps["role"]) {
  return role === "company" ? "/company/support" : "/corper/support";
}

function buildFaqRoute(role: SupportPageProps["role"]) {
  return role === "company" ? "/company/faq" : "/corper/faq";
}

function buildDashboardRoute(role: SupportPageProps["role"]) {
  return role === "company" ? "/company/dashboard" : "/corper/dashboard";
}

export function SupportPage({ role }: SupportPageProps) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [portalReady, setPortalReady] = useState(false);
  const [emailForm, setEmailForm] = useState<EmailFormState>({
    subject: role === "company" ? "Account" : "Verification help",
    message: "",
  });
  const [improvementForm, setImprovementForm] = useState<ImprovementFormState>({
    title: "",
    idea: "",
  });

  useEffect(() => {
    setPortalReady(true);
    return () => setPortalReady(false);
  }, []);

  async function handleEmailSupportSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!emailForm.message.trim()) {
      toast.error("Enter your support message before sending.");
      return;
    }

    try {
      await apiFetch<{ message: string }>("/common/support-messages/", {
        method: "POST",
        body: JSON.stringify({
          kind: "support",
          topic: emailForm.subject,
          message: emailForm.message.trim(),
        }),
      });
      toast.success("Message sent.");
      setEmailForm((current) => ({ ...current, message: "" }));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to send message.");
    }
  }

  async function handleImprovementSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!improvementForm.title.trim() || !improvementForm.idea.trim()) {
      toast.error("Enter both an improvement title and description.");
      return;
    }

    try {
      await apiFetch<{ message: string }>("/common/support-messages/", {
        method: "POST",
        body: JSON.stringify({
          kind: "improvement",
          title: improvementForm.title.trim(),
          message: improvementForm.idea.trim(),
        }),
      });
      toast.success("Suggestion sent.");
      setImprovementForm({ title: "", idea: "" });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to send suggestion.");
    }
  }

  const callSupportCard = (
    <Card className="grid h-full min-h-[9rem] gap-4">
      <div className="flex items-start gap-4">
        <SupportIconFrame tone="amber">
          <PhoneCall className="h-6 w-6" />
        </SupportIconFrame>
      </div>
      <div>
        <h3 className="font-display text-xl text-lime">Call</h3>
        <p className="mt-2 text-sm leading-7 text-mist">
          Speak with the support team for urgent matters.
        </p>
      </div>
      <div className="mt-auto">
        <a
          href={`tel:${SUPPORT_PHONE}`}
          className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
        >
          Call {SUPPORT_PHONE_DISPLAY}
        </a>
      </div>
    </Card>
  );

  const emailSupportCard = (
    <Card className="grid h-full min-h-[9rem] gap-4">
      <div className="flex items-start gap-4">
        <SupportIconFrame tone="coral">
          <Mail className="h-6 w-6" />
        </SupportIconFrame>
      </div>
      <div>
        <h3 className="font-display text-xl text-lime">Email</h3>
        <p className="mt-2 text-sm leading-7 text-mist">
          For none urgent but important issues with longer case notes.
        </p>
      </div>
      <div className="mt-auto">
        <a
          href={`mailto:${SUPPORT_EMAIL}`}
          className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
        >
          email: {SUPPORT_EMAIL}
        </a>
      </div>
    </Card>
  );

  const floatingChat = portalReady
    ? createPortal(
      <>
        {isChatOpen ? (
          <div className="fixed bottom-24 right-2 z-[100] w-[min(24rem,calc(100vw-1rem))] sm:bottom-24 sm:right-4">
            <Card className="grid gap-4 border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.1),rgba(4,21,15,0.08)),linear-gradient(180deg,rgba(11,38,27,0.96),rgba(7,20,14,0.98))] shadow-[0_24px_60px_rgba(0,0,0,0.35)]">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <SupportIconFrame tone="sky">
                    <MessageSquare className="h-5 w-5" />
                  </SupportIconFrame>
                  <div>
                    <h3 className="font-display text-xl text-lime">Chat with support</h3>
                    <p className="mt-1 text-xs text-mist">Real-time support chat is coming soon.</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsChatOpen(false)}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/12 bg-white/[0.06] text-white transition hover:border-lime/70 hover:bg-white/[0.12]"
                  aria-label="Close support chat"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-black/12 p-5">
                <p className="text-sm leading-7 text-mist">
                  Use the support form, direct phone line, or email support while chat is being prepared.
                </p>
              </div>
            </Card>
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => setIsChatOpen((current) => !current)}
          className="fixed bottom-2 right-2 z-[100] inline-flex h-14 w-14 items-center justify-center rounded-full border border-lime/35 bg-[linear-gradient(135deg,#1FB766_0%,#118A48_100%)] text-[#E6D28C] shadow-[0_18px_35px_rgba(17,138,72,0.32)] transition hover:scale-105 hover:brightness-105 sm:bottom-4 sm:right-4"
          aria-label={isChatOpen ? "Hide support chat" : "Open support chat"}
        >
          <MessageSquare className="h-6 w-6" />
        </button>
      </>,
      document.body
    )
    : null;

  return (
    <>
      <DashboardShell role={role} title="Support center" hideDefaultHeaderAside>
        <div className="grid gap-5">
          <Card className="relative overflow-hidden border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.1),rgba(4,21,15,0.04)),radial-gradient(circle_at_top_right,rgba(124,217,161,0.22),transparent_42%),radial-gradient(circle_at_bottom_left,rgba(56,189,248,0.14),transparent_34%),linear-gradient(180deg,#143B2A_0%,#091D14_100%)]">
            <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_50%)] lg:block" />
            <div className="relative grid gap-5">
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)] lg:items-end">
                <div>
                  <h2 className="font-display text-2xl leading-tight text-white sm:text-[1.8rem]">
                    Get help.
                  </h2>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-white/78">
                    See the FAQ page for answers to general questions, contact support if you need further assistance.
                  </p>
                  <div className="mt-5 flex flex-wrap gap-3">
                    <Link
                      href={buildFaqRoute(role)}
                      className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
                    >
                      Open FAQ
                    </Link>
                  </div>
                </div>
                <div className="grid gap-3 rounded-[24px] border border-white/10 bg-black/10 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-lime">Direct contacts</p>
                  <a
                    href={`tel:${SUPPORT_PHONE}`}
                    className="text-lg font-semibold text-white transition hover:text-lime"
                  >
                    {SUPPORT_PHONE_DISPLAY}
                  </a>
                  <a
                    href={`mailto:${SUPPORT_EMAIL}`}
                    className="text-sm text-mist transition hover:text-white"
                  >
                    {SUPPORT_EMAIL}
                  </a>
                </div>
              </div>
            </div>
          </Card>

          <div className="grid items-stretch gap-5 md:grid-cols-2">
            {callSupportCard}
            {emailSupportCard}
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card className="grid gap-4">
              <div className="flex items-start gap-4">
                <SupportIconFrame tone="coral">
                  <Mail className="h-6 w-6" />
                </SupportIconFrame>
              </div>
              <div>
                <h3 className="font-display text-2xl text-lime">Issues</h3>
              </div>
              <form onSubmit={handleEmailSupportSubmit} className="grid gap-4">
                <label className="grid gap-2 text-sm text-mist">
                  <span>Topic</span>
                  <Select
                    value={emailForm.subject}
                    onChange={(event) => setEmailForm((current) => ({ ...current, subject: event.target.value }))}
                  >
                    <option value="Verification help">Verification</option>
                    <option value="Account">Account</option>
                    <option value="Billing">Billing</option>
                    <option value="Profile">Profile</option>
                    <option value="Subscription">Subscription</option>
                    <option value="Payments">Payments</option>
                    <option value="Technical issues">Technical issues</option>
                    <option value="Other">Other</option>
                  </Select>
                </label>
                <label className="grid gap-2 text-sm text-mist">
                  <span>Message</span>
                  <Textarea
                    value={emailForm.message}
                    onChange={(event) => setEmailForm((current) => ({ ...current, message: event.target.value }))}
                    placeholder="Describe the issue, what you expected, and what actually happened."
                    required
                  />
                </label>
                <Button type="submit">Send message</Button>
              </form>
            </Card>

            <Card className="grid gap-4">
              <div className="flex items-start gap-4">
                <SupportIconFrame tone="sky">
                  <Lightbulb className="h-6 w-6" />
                </SupportIconFrame>
              </div>
              <div>
                <h3 className="font-display text-2xl text-lime">Feedback?</h3>
              </div>
              <form onSubmit={handleImprovementSubmit} className="grid gap-4">
                <label className="grid gap-2 text-sm text-mist">
                  <span>Title</span>
                  <Input
                    value={improvementForm.title}
                    onChange={(event) => setImprovementForm((current) => ({ ...current, title: event.target.value }))}
                    placeholder="Example: Add better document review updates"
                    required
                  />
                </label>
                <label className="grid gap-2 text-sm text-mist">
                  <span>Message</span>
                  <Textarea
                    value={improvementForm.idea}
                    onChange={(event) => setImprovementForm((current) => ({ ...current, idea: event.target.value }))}
                    placeholder="Explain the improvement and how it would help corpers or companies."
                    required
                  />
                </label>
                <Button type="submit" variant="secondary">Send</Button>
              </form>
            </Card>
          </div>

          <Card className="grid gap-4 border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(4,21,15,0.05)),linear-gradient(180deg,rgba(11,38,27,0.92),rgba(7,20,14,0.96))]">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-lime">Satisfied with the assistance offered?</p>
                <h3 className="mt-2 font-display text-xl text-white">Return to your workspace anytime.</h3>
              </div>
              <Link
                href={buildDashboardRoute(role)}
                className="inline-flex items-center justify-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-ink transition duration-200 hover:bg-lime hover:text-[#E6D28C]"
              >
                Back to Overview
              </Link>
            </div>
          </Card>

        </div>
      </DashboardShell>
      {floatingChat}
    </>
  );
}

export function SupportFaqPage({
  role,
  faqItems,
}: SupportPageProps & { faqItems: SupportFaqItem[] }) {
  const [activeQuestion, setActiveQuestion] = useState<string | null>(faqItems[0]?.question ?? null);

  return (
    <DashboardShell role={role} title="Frequently asked questions" hideDefaultHeaderAside>
      <div className="grid gap-5">
        <Card className="relative overflow-hidden border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.1),rgba(4,21,15,0.04)),radial-gradient(circle_at_top_right,rgba(244,211,94,0.18),transparent_42%),linear-gradient(180deg,#143B2A_0%,#091D14_100%)]">
          <div className="grid gap-5">
            <Badge className="w-fit border-[#F4D35E]/30 bg-[#F4D35E]/10 text-[#F7E29A]">FAQ</Badge>
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_auto] lg:items-end">
              <div>
                <p className="font-display text-lg leading-tight text-white sm:text-[1.0rem]">
                  Find answers to commonly asked questions.
                </p>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-white/78">
                  Find the answers to the most common support questions here. Return to the support page if you still need help.
                </p>
              </div>
              <Link
                href={buildSupportRoute(role)}
                className="inline-flex items-center justify-center rounded-full border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-semibold text-lime transition duration-200 hover:border-lime/70 hover:bg-white/[0.14]"
              >
                Back to support
              </Link>
            </div>
          </div>
        </Card>

        <div className="grid gap-3">
          {faqItems.map((item) => (
            <button
              key={item.question}
              type="button"
              onClick={() =>
                setActiveQuestion((current) => (current === item.question ? null : item.question))
              }
              className="w-full text-left"
            >
              <Card className="grid gap-0 overflow-hidden p-0 px-1 py-1">
                <div className="flex items-center justify-between gap-2 px-1 py-1">
                  <div className="flex items-center gap-1 px-0.4 py-0.5">
                    <CircleHelp className="h-6.5 w-6.5" stroke="#C2B280" />
                    <h3 className="font-display text-[1.0rem] text-yellow">{item.question}</h3>
                  </div>
                  <Badge className="text-yellow px-1 py-0.5">
                    {activeQuestion === item.question ? "Hide" : "Show"}
                  </Badge>
                </div>
                {activeQuestion === item.question ? (
                  <div className="border-t border-white/10 px-2 py-1">
                    <p className="whitespace-pre-line text-sm leading-7 text-mist">{item.answer}</p>
                  </div>
                ) : null}
              </Card>
            </button>
          ))}
        </div>

        <Card className="grid gap-4 border-white/12 bg-[linear-gradient(145deg,rgba(255,255,255,0.08),rgba(4,21,15,0.05)),linear-gradient(180deg,rgba(11,38,27,0.92),rgba(7,20,14,0.96))]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Still need help?</p>
              <h3 className="mt-2 font-display text-2xl text-white">Continue in the support center.</h3>
            </div>
            <Link
              href={buildSupportRoute(role)}
              className="inline-flex items-center justify-center rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-ink transition duration-200 hover:bg-lime hover:text-[#E6D28C]"
            >
              Open support
            </Link>
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}
