import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VerifyEmailForm } from "@/components/forms/verify-email-form";
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

describe("VerifyEmailForm", () => {
  beforeEach(() => {
    pushMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
    vi.mocked(apiFetch).mockReset();
  });

  it("redirects verified users to sign in with their email prefilled", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ message: "ok" });

    render(<VerifyEmailForm defaultEmail="corper@example.com" />);

    fireEvent.change(screen.getByPlaceholderText("6-character code"), {
      target: { value: "A1B2C3" }
    });
    fireEvent.submit(screen.getByRole("button", { name: "Verify email" }).closest("form")!);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/auth/verify-email/",
        expect.objectContaining({
          auth: false,
          method: "POST",
            body: JSON.stringify({
              email: "corper@example.com",
              code: "A1B2C3"
            })
          })
      );
      expect(pushMock).toHaveBeenCalledWith("/login/?email=corper%40example.com");
    });
  });
});
