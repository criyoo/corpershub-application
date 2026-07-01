"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ChangeEvent, type FormEvent } from "react";
import { toast } from "sonner";

import { useAuth } from "@/components/providers/auth-provider";
import { DashboardShell } from "@/components/layout/dashboard-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useApiQuery } from "@/hooks/use-api-query";
import { apiFetch } from "@/lib/api";
import { type SessionUser, type UserRole } from "@/lib/session";

type AccountSettings = {
  email: string;
  role: UserRole;
  mobile_number: string;
  profile_completed: boolean;
  profile_path: string;
  profile_visibility_paused: boolean;
};

type UserResponse = {
  message: string;
  user: SessionUser;
};

type MobileResponse = UserResponse & {
  mobile_number: string;
};

type ProfileVisibilityResponse = {
  message: string;
  profile_visibility_paused: boolean;
};

type CompanyOTPRequestResponse = {
  message: string;
  action: string;
  target_email: string;
};

type PasswordForm = {
  new_password: string;
  confirm_password: string;
  otp_code: string;
};

type EmailForm = {
  current_password: string;
  new_email: string;
  otp_code: string;
};

type MobileForm = {
  mobile_number: string;
  current_password: string;
  otp_code: string;
};

type DeleteForm = {
  current_password: string;
  otp_code: string;
};

const EMPTY_PASSWORD_FORM: PasswordForm = {
  new_password: "",
  confirm_password: "",
  otp_code: "",
};

const EMPTY_EMAIL_FORM: EmailForm = {
  current_password: "",
  new_email: "",
  otp_code: "",
};

const EMPTY_MOBILE_FORM: MobileForm = {
  mobile_number: "",
  current_password: "",
  otp_code: "",
};

const EMPTY_DELETE_FORM: DeleteForm = {
  current_password: "",
  otp_code: "",
};

export function AccountSettingsPage({ role }: { role: Exclude<UserRole, "admin"> }) {
  const router = useRouter();
  const { session, updateSession } = useAuth();
  const settings = useApiQuery<AccountSettings>("/auth/settings/");
  const [passwordForm, setPasswordForm] = useState<PasswordForm>(EMPTY_PASSWORD_FORM);
  const [emailForm, setEmailForm] = useState<EmailForm>(EMPTY_EMAIL_FORM);
  const [mobileForm, setMobileForm] = useState<MobileForm>(EMPTY_MOBILE_FORM);
  const [deleteForm, setDeleteForm] = useState<DeleteForm>(EMPTY_DELETE_FORM);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [companyOtpStep, setCompanyOtpStep] = useState({
    password: false,
    email: false,
    mobile: false,
    delete: false,
  });

  function updateSessionUser(nextUser: SessionUser) {
    if (!session) {
      return;
    }
    updateSession({
      ...session,
      user: nextUser,
    });
  }

  function handlePasswordFieldChange(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setPasswordForm((current) => ({
      ...current,
      ...(role === "company" && companyOtpStep.password && name !== "otp_code" ? { otp_code: "" } : {}),
      [name]: value,
    }));
    if (role === "company" && companyOtpStep.password && name !== "otp_code") {
      setCompanyOtpPhase("password", false);
    }
  }

  function handleEmailFieldChange(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setEmailForm((current) => ({
      ...current,
      ...(role === "company" && companyOtpStep.email && name !== "otp_code" ? { otp_code: "" } : {}),
      [name]: value,
    }));
    if (role === "company" && companyOtpStep.email && name !== "otp_code") {
      setCompanyOtpPhase("email", false);
    }
  }

  function handleMobileFieldChange(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setMobileForm((current) => ({
      ...current,
      ...(role === "company" && companyOtpStep.mobile && name !== "otp_code" ? { otp_code: "" } : {}),
      [name]: value,
    }));
    if (role === "company" && companyOtpStep.mobile && name !== "otp_code") {
      setCompanyOtpPhase("mobile", false);
    }
  }

  function handleDeleteFieldChange(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setDeleteForm((current) => ({
      ...current,
      ...(role === "company" && companyOtpStep.delete && name !== "otp_code" ? { otp_code: "" } : {}),
      [name]: value,
    }));
    if (role === "company" && companyOtpStep.delete && name !== "otp_code") {
      setCompanyOtpPhase("delete", false);
    }
  }

  function setCompanyOtpPhase(section: "password" | "email" | "mobile" | "delete", enabled: boolean) {
    setCompanyOtpStep((current) => ({
      ...current,
      [section]: enabled,
    }));
  }

  async function requestCompanyOtp(
    section: "password" | "email" | "mobile" | "delete",
    body: Record<string, string>
  ) {
    const response = await apiFetch<CompanyOTPRequestResponse>("/auth/settings/company-otp/request/", {
      method: "POST",
      body: JSON.stringify(body),
    });
    setCompanyOtpPhase(section, true);
    toast.success(`${response.message} Sent to ${response.target_email}.`);
  }

  async function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      toast.error("New password and confirmation do not match.");
      return;
    }

    setActiveSection("password");
    try {
      if (role === "company") {
        if (!companyOtpStep.password) {
          await requestCompanyOtp("password", {
            action: "change_password",
            new_password: passwordForm.new_password,
          });
          return;
        }
        const response = await apiFetch<{ message: string }>("/auth/settings/company-otp/confirm/", {
          method: "POST",
          body: JSON.stringify({
            action: "change_password",
            new_password: passwordForm.new_password,
            otp_code: passwordForm.otp_code,
          }),
        });
        toast.success(response.message);
        setPasswordForm(EMPTY_PASSWORD_FORM);
        setCompanyOtpPhase("password", false);
        return;
      }
      const response = await apiFetch<{ message: string }>("/auth/settings/change-password/", {
        method: "POST",
        body: JSON.stringify({
          new_password: passwordForm.new_password,
        }),
      });
      toast.success(response.message);
      setPasswordForm(EMPTY_PASSWORD_FORM);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update password.");
    } finally {
      setActiveSection(null);
    }
  }

  async function handleEmailSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setActiveSection("email");
    try {
      if (role === "company") {
        if (!companyOtpStep.email) {
          await requestCompanyOtp("email", {
            action: "change_email",
            current_password: emailForm.current_password,
            new_email: emailForm.new_email,
          });
          return;
        }
        const response = await apiFetch<UserResponse>("/auth/settings/company-otp/confirm/", {
          method: "POST",
          body: JSON.stringify({
            action: "change_email",
            current_password: emailForm.current_password,
            new_email: emailForm.new_email,
            otp_code: emailForm.otp_code,
          }),
        });
        updateSessionUser(response.user);
        await settings.refetch();
        setEmailForm(EMPTY_EMAIL_FORM);
        setCompanyOtpPhase("email", false);
        toast.success(response.message);
        return;
      }
      const response = await apiFetch<UserResponse>("/auth/settings/change-email/", {
        method: "POST",
        body: JSON.stringify(emailForm),
      });
      updateSessionUser(response.user);
      await settings.refetch();
      setEmailForm(EMPTY_EMAIL_FORM);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update email.");
    } finally {
      setActiveSection(null);
    }
  }

  async function handleMobileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setActiveSection("mobile");
    try {
      if (role === "company") {
        if (!companyOtpStep.mobile) {
          await requestCompanyOtp("mobile", {
            action: "change_mobile_number",
            current_password: mobileForm.current_password,
            mobile_number: mobileForm.mobile_number,
          });
          return;
        }
        const response = await apiFetch<MobileResponse>("/auth/settings/company-otp/confirm/", {
          method: "POST",
          body: JSON.stringify({
            action: "change_mobile_number",
            current_password: mobileForm.current_password,
            mobile_number: mobileForm.mobile_number,
            otp_code: mobileForm.otp_code,
          }),
        });
        updateSessionUser(response.user);
        await settings.refetch();
        setMobileForm(EMPTY_MOBILE_FORM);
        setCompanyOtpPhase("mobile", false);
        toast.success(response.message);
        return;
      }
      const response = await apiFetch<MobileResponse>("/auth/settings/change-mobile-number/", {
        method: "POST",
        body: JSON.stringify(mobileForm),
      });
      updateSessionUser(response.user);
      await settings.refetch();
      setMobileForm(EMPTY_MOBILE_FORM);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update mobile number.");
    } finally {
      setActiveSection(null);
    }
  }

  async function handleDeleteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setActiveSection("delete");
    try {
      if (role === "company") {
        if (!companyOtpStep.delete) {
          await requestCompanyOtp("delete", {
            action: "delete_account",
            current_password: deleteForm.current_password,
          });
          return;
        }
        const response = await apiFetch<{ message: string }>("/auth/settings/company-otp/confirm/", {
          method: "POST",
          body: JSON.stringify({
            action: "delete_account",
            current_password: deleteForm.current_password,
            otp_code: deleteForm.otp_code,
          }),
        });
        updateSession(null);
        toast.success(response.message);
        router.replace("/");
        return;
      }
      const response = await apiFetch<{ message: string }>("/auth/settings/delete-account/", {
        method: "POST",
        body: JSON.stringify(deleteForm),
      });
      updateSession(null);
      toast.success(response.message);
      router.replace("/");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to delete account.");
    } finally {
      setActiveSection(null);
    }
  }

  async function handleProfileVisibilityToggle() {
    if (!settings.data) {
      return;
    }

    setActiveSection("visibility");
    try {
      const response = await apiFetch<ProfileVisibilityResponse>("/auth/settings/profile-visibility/", {
        method: "PATCH",
        body: JSON.stringify({
          profile_visibility_paused: !settings.data.profile_visibility_paused,
        }),
      });
      await settings.refetch();
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Unable to update profile visibility.");
    } finally {
      setActiveSection(null);
    }
  }

  const mobileLabel = role === "company" ? "Contact phone" : "Mobile number";
  const companyUsesOtp = role === "company";
  const shouldOpenProfileInEditMode =
    settings.data &&
    (role === "company" ||
      settings.data.profile_path === "/corper/profile" ||
      settings.data.profile_path.startsWith("/corper/profile?"));
  const profileEditorHref =
    settings.data && shouldOpenProfileInEditMode
      ? `${settings.data.profile_path}${settings.data.profile_path.includes("?") ? "&" : "?"}edit=1`
      : settings.data?.profile_path ?? "#";
  const profileVisibilityPaused = settings.data?.profile_visibility_paused ?? false;
  const visibilityTitle = profileVisibilityPaused ? "Profile visibility paused" : "Profile visible in discovery";
  const visibilityDescription =
    role === "company"
      ? "When paused, your company photo card will not appear on the Discover Companies page for corpers."
      : "When paused, your corper photo card will not appear on the Discover Corpers page for companies.";

  return (
    <DashboardShell role={role} title="Settings">
      {!settings.data && settings.loading ? (
        <Card>
          <p className="text-sm text-mist">Loading settings...</p>
        </Card>
      ) : settings.error || !settings.data ? (
        <Card>
          <p className="text-sm text-mist">{settings.error ?? "Unable to load settings right now."}</p>
        </Card>
      ) : (
        <div className="grid gap-4">
          <Card className="grid gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Update Profile</p>
              <h2 className="mt-3 font-display text-2xl text-white">
                {role === "company" ? "Edit your company profile" : "Update your corper profile"}
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-mist">
                {role === "company"
                  ? "Open the company profile in edit mode."
                  : "Open your profile in edit mode to update your gender, photo, posting state, primary skill, and bio."}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={profileEditorHref}
                className="inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#1FB766_0%,#118A48_100%)] px-5 py-2.5 text-sm font-semibold text-[#E6D28C] shadow-[0_18px_35px_rgba(17,138,72,0.28)] transition duration-200 hover:brightness-105"
              >
                {role === "company" ? "Edit Profile" : "Update profile"}
              </Link>
            </div>
          </Card>

          <Card className="grid gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Profile Visibility</p>
              <h2 className="mt-3 font-display text-2xl text-white">{visibilityTitle}</h2>
              <p className="mt-2 max-w-2xl text-sm text-mist">{visibilityDescription}</p>
              <p className="mt-2 max-w-2xl text-sm text-mist">
                This only affects discovery cards. You can still sign in and use the rest of your dashboard while visibility is paused.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" onClick={handleProfileVisibilityToggle} disabled={activeSection === "visibility"}>
                {activeSection === "visibility"
                  ? "Updating..."
                  : profileVisibilityPaused
                    ? "Unpause visibility"
                    : "Pause visibility"}
              </Button>
            </div>
          </Card>

          <Card className="grid gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Change Password</p>
              <h2 className="mt-3 font-display text-2xl text-white">Update your sign-in password</h2>
              {companyUsesOtp ? (
                <p className="mt-2 max-w-2xl text-sm text-mist">
                  We will send a verification code to your current email before the password change is applied.
                </p>
              ) : null}
            </div>
            <form
              className={`grid gap-4 ${companyUsesOtp && companyOtpStep.password ? "md:grid-cols-3" : "md:grid-cols-2"}`}
              onSubmit={handlePasswordSubmit}
            >
              <label className="grid gap-2 text-sm text-mist">
                <span>New password</span>
                <Input
                  name="new_password"
                  type="password"
                  value={passwordForm.new_password}
                  onChange={handlePasswordFieldChange}
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-mist">
                <span>Confirm new password</span>
                <Input
                  name="confirm_password"
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={handlePasswordFieldChange}
                  required
                />
              </label>
              {companyUsesOtp && companyOtpStep.password ? (
                <label className="grid gap-2 text-sm text-mist">
                  <span>Email OTP</span>
                  <Input
                    name="otp_code"
                    value={passwordForm.otp_code}
                    onChange={handlePasswordFieldChange}
                    placeholder="enter 6-digit code"
                    required
                  />
                </label>
              ) : null}
              <div className={companyUsesOtp && companyOtpStep.password ? "md:col-span-3" : "md:col-span-2"}>
                <Button type="submit" disabled={activeSection === "password"}>
                  {activeSection === "password"
                    ? companyOtpStep.password
                      ? "Confirming..."
                      : "Sending OTP..."
                    : companyUsesOtp
                      ? companyOtpStep.password
                        ? "Confirm password change"
                        : "Send OTP"
                      : "Change password"}
                </Button>
              </div>
            </form>
          </Card>

          <Card className="grid gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Change Email</p>
              <h2 className="mt-3 font-display text-2xl text-white">Update your account email</h2>
              {companyUsesOtp ? (
                <p className="mt-2 max-w-2xl text-sm text-mist">
                  We will send a verification code to the new email address before switching your login email.
                </p>
              ) : null}
            </div>
            <form
              className={`grid gap-4 ${companyUsesOtp && companyOtpStep.email ? "md:grid-cols-4" : "md:grid-cols-[1.2fr_1fr_auto]"}`}
              onSubmit={handleEmailSubmit}
            >
              <label className="grid gap-2 text-sm text-mist">
                <span>New email</span>
                <Input
                  name="new_email"
                  type="email"
                  value={emailForm.new_email}
                  onChange={handleEmailFieldChange}
                  placeholder="enter new email"
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-mist">
                <span>Password</span>
                <Input
                  name="current_password"
                  type="password"
                  value={emailForm.current_password}
                  onChange={handleEmailFieldChange}
                  placeholder="enter password"
                  required
                />
              </label>
              {companyUsesOtp && companyOtpStep.email ? (
                <label className="grid gap-2 text-sm text-mist">
                  <span>Email OTP</span>
                  <Input
                    name="otp_code"
                    value={emailForm.otp_code}
                    onChange={handleEmailFieldChange}
                    placeholder="enter 6-digit code"
                    required
                  />
                </label>
              ) : null}
              <div className="flex items-end">
                <Button type="submit" disabled={activeSection === "email"}>
                  {activeSection === "email"
                    ? companyOtpStep.email
                      ? "Confirming..."
                      : "Sending OTP..."
                    : companyUsesOtp
                      ? companyOtpStep.email
                        ? "Confirm email change"
                        : "Send OTP"
                      : "Change email"}
                </Button>
              </div>
            </form>
          </Card>

          <Card className="grid gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-lime">Change Mobile Number</p>
              <h2 className="mt-3 font-display text-2xl text-white">Update your {mobileLabel.toLowerCase()}</h2>
              {companyUsesOtp ? (
                <p className="mt-2 max-w-2xl text-sm text-mist">
                  We will send a verification code to your current email before updating the contact phone.
                </p>
              ) : null}
            </div>
            <form
              className={`grid gap-4 ${companyUsesOtp && companyOtpStep.mobile ? "md:grid-cols-4" : "md:grid-cols-[1.2fr_1fr_auto]"}`}
              onSubmit={handleMobileSubmit}
            >
              <label className="grid gap-2 text-sm text-mist">
                <span>{mobileLabel}</span>
                <Input
                  name="mobile_number"
                  value={mobileForm.mobile_number}
                  onChange={handleMobileFieldChange}
                  placeholder={role === "company" ? "enter new contact phone" : "enter new mobile number"}
                  required
                />
              </label>
              <label className="grid gap-2 text-sm text-mist">
                <span>Password</span>
                <Input
                  name="current_password"
                  type="password"
                  value={mobileForm.current_password}
                  onChange={handleMobileFieldChange}
                  placeholder="enter password"
                  required
                />
              </label>
              {companyUsesOtp && companyOtpStep.mobile ? (
                <label className="grid gap-2 text-sm text-mist">
                  <span>Email OTP</span>
                  <Input
                    name="otp_code"
                    value={mobileForm.otp_code}
                    onChange={handleMobileFieldChange}
                    placeholder="enter 6-digit code"
                    required
                  />
                </label>
              ) : null}
              <div className="flex items-end">
                <Button type="submit" disabled={activeSection === "mobile"}>
                  {activeSection === "mobile"
                    ? companyOtpStep.mobile
                      ? "Confirming..."
                      : "Sending OTP..."
                    : companyUsesOtp
                      ? companyOtpStep.mobile
                        ? "Confirm mobile change"
                        : "Send OTP"
                      : "Change mobile number"}
                </Button>
              </div>
            </form>
          </Card>

          <Card className="grid gap-4 border-coral/30 bg-coral/10">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-coral">Delete Account</p>
              <h2 className="mt-3 font-display text-2xl text-white">Permanently remove this account</h2>
              <p className="mt-2 max-w-2xl text-sm text-mist">
                {companyUsesOtp
                  ? "We will send a verification code to your current email before the account is deactivated and archived."
                  : "This deactivates your account and archives its records for recovery checks. Sign-in access is removed immediately."}
              </p>
            </div>
            <form
              className={`grid gap-4 ${companyUsesOtp && companyOtpStep.delete ? "md:grid-cols-[1fr_1fr_auto]" : "md:grid-cols-[1fr_auto]"}`}
              onSubmit={handleDeleteSubmit}
            >
              <label className="grid gap-2 text-sm text-mist">
                <span>Password</span>
                <Input
                  name="current_password"
                  type="password"
                  value={deleteForm.current_password}
                  onChange={handleDeleteFieldChange}
                  required
                />
              </label>
              {companyUsesOtp && companyOtpStep.delete ? (
                <label className="grid gap-2 text-sm text-mist">
                  <span>Email OTP</span>
                  <Input
                    name="otp_code"
                    value={deleteForm.otp_code}
                    onChange={handleDeleteFieldChange}
                    placeholder="enter 6-digit code"
                    required
                  />
                </label>
              ) : null}
              <div className="flex items-end">
                <Button type="submit" variant="danger" disabled={activeSection === "delete"}>
                  {activeSection === "delete"
                    ? companyOtpStep.delete
                      ? "Confirming..."
                      : "Sending OTP..."
                    : companyUsesOtp
                      ? companyOtpStep.delete
                        ? "Confirm account deletion"
                        : "Send OTP"
                      : "Delete account"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}
