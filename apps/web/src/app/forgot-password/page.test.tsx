import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordPage from "@/app/forgot-password/page";
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

describe("ForgotPasswordPage", () => {
  beforeEach(() => {
    pushMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
    vi.mocked(apiFetch).mockReset();
  });

  it("redirects to the reset-code verification page after sending the reset code", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ message: "If the account exists, a reset code has been sent." });

    render(<ForgotPasswordPage />);

    fireEvent.change(screen.getByPlaceholderText("Email address"), {
      target: { value: "corper@example.com" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Send reset code" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/forgot-password/",
        expect.objectContaining({
          auth: false,
          method: "POST",
          body: JSON.stringify({ email: "corper@example.com" }),
        }),
      );
      expect(pushMock).toHaveBeenCalledWith("/reset-password?email=corper%40example.com");
    });
  });
});
