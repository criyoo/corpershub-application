import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RegisterForm } from "@/components/forms/register-form";
import { apiFetch } from "@/lib/api";

const { pushMock, toastSuccessMock, toastErrorMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: toastSuccessMock,
    error: toastErrorMock,
  },
}));

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

describe("RegisterForm", () => {
  beforeEach(() => {
    pushMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
    vi.mocked(apiFetch).mockReset();
  });

  it("redirects to email verification without pre-populating the OTP code", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      email: "corper@example.com",
      role: "corper",
      message: "Verification code sent. Complete email verification to finish creating your account.",
    });

    render(<RegisterForm role="corper" />);

    expect(screen.queryByText("Choose plan")).not.toBeInTheDocument();
    expect(screen.queryByText("7 Days Free Trial")).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Email address"), {
      target: { value: "corper@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Create a password"), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Continue" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/register/",
        expect.objectContaining({
          auth: false,
          method: "POST",
          body: JSON.stringify({
            email: "corper@example.com",
            password: "StrongPass123!",
            role: "corper",
          }),
        }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith(
        "Verification code sent. Complete email verification to finish creating your account."
      );
      expect(pushMock).toHaveBeenCalledWith("/verify-email?email=corper%40example.com");
    });
  });

  it("shows only the company signup email and password fields", () => {
    render(<RegisterForm role="company" />);

    expect(screen.queryByPlaceholderText("Company registration number")).not.toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("Company name will be filled automatically")
    ).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("Work email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Create a password")).toBeInTheDocument();
  });

  it("submits company signup without company profile fields", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      email: "owner@example.com",
      role: "company",
      message: "Verification code sent. Complete email verification to finish creating your account.",
    });

    render(<RegisterForm role="company" />);

    fireEvent.change(screen.getByPlaceholderText("Work email"), {
      target: { value: "owner@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Create a password"), {
      target: { value: "CompanyPass123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Continue" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/register/",
        expect.objectContaining({
          auth: false,
          method: "POST",
          body: JSON.stringify({
            email: "owner@example.com",
            password: "CompanyPass123!",
            role: "company",
          }),
        }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith(
        "Verification code sent. Complete email verification to finish creating your account."
      );
      expect(pushMock).toHaveBeenCalledWith("/verify-email?email=owner%40example.com");
    });
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });
});
