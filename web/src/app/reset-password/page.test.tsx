import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResetPasswordPage from "@/app/reset-password/page";
import { apiFetch } from "@/lib/api";

const { pushMock, toastSuccessMock, toastErrorMock, searchParamsState } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
  searchParamsState: {
    email: null as string | null,
    token: null as string | null,
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useSearchParams: () => ({
    get: (key: string) => searchParamsState[key as "email" | "token"] ?? null,
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

describe("ResetPasswordPage", () => {
  beforeEach(() => {
    pushMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
    vi.mocked(apiFetch).mockReset();
    searchParamsState.email = null;
    searchParamsState.token = null;
  });

  it("verifies the reset code before routing to the new password step", async () => {
    searchParamsState.email = "corper@example.com";
    vi.mocked(apiFetch).mockResolvedValue({
      message: "Reset code verified.",
      reset_token: "verified-reset-token",
      email: "corper@example.com",
    });

    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByPlaceholderText("6-character reset code"), {
      target: { value: "A1B2C3" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Verify reset code" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/reset-password/verify-code/",
        expect.objectContaining({
          auth: false,
          method: "POST",
          body: JSON.stringify({
            email: "corper@example.com",
            code: "A1B2C3",
          }),
        }),
      );
      expect(pushMock).toHaveBeenCalledWith(
        "/reset-password?token=verified-reset-token&email=corper%40example.com"
      );
    });
  });

  it("submits the new password after the reset code has been verified", async () => {
    searchParamsState.email = "corper@example.com";
    searchParamsState.token = "verified-reset-token";
    vi.mocked(apiFetch).mockResolvedValue({ message: "Password reset successful." });

    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByPlaceholderText("New password"), {
      target: { value: "NewPass123!" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm new password"), {
      target: { value: "NewPass123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Change password" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/reset-password/",
        expect.objectContaining({
          auth: false,
          method: "POST",
          body: JSON.stringify({
            reset_token: "verified-reset-token",
            new_password: "NewPass123!",
          }),
        }),
      );
      expect(pushMock).toHaveBeenCalledWith("/login/?email=corper%40example.com");
    });
  });

  it("does not submit when the password confirmation does not match", async () => {
    searchParamsState.email = "corper@example.com";
    searchParamsState.token = "verified-reset-token";

    render(<ResetPasswordPage />);

    fireEvent.change(screen.getByPlaceholderText("New password"), {
      target: { value: "NewPass123!" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm new password"), {
      target: { value: "Mismatch123!" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Change password" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).not.toHaveBeenCalled();
      expect(toastErrorMock).toHaveBeenCalledWith("Passwords do not match.");
    });
  });

  it("toggles password visibility independently on the reset form", () => {
    searchParamsState.email = "corper@example.com";
    searchParamsState.token = "verified-reset-token";

    render(<ResetPasswordPage />);

    const newPasswordInput = screen.getByPlaceholderText("New password");
    const confirmPasswordInput = screen.getByPlaceholderText("Confirm new password");
    const toggleButtons = screen.getAllByRole("button", { name: "Show password" });

    expect(newPasswordInput).toHaveAttribute("type", "password");
    expect(confirmPasswordInput).toHaveAttribute("type", "password");

    fireEvent.click(toggleButtons[0]);

    expect(newPasswordInput).toHaveAttribute("type", "text");
    expect(confirmPasswordInput).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: "Hide password" })).toBeInTheDocument();
  });
});
