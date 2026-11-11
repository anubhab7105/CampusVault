import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  googleAuthorize: vi.fn(),
  requestTeacherOtp: vi.fn(),
  verifyTeacherOtp: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  setTokens: vi.fn(),
  setUser: vi.fn(),
}));

vi.mock("@services/authService", () => ({
  authService: {
    googleAuthorize: (...args: unknown[]) => mocks.googleAuthorize(...args),
    requestTeacherOtp: (...args: unknown[]) => mocks.requestTeacherOtp(...args),
    verifyTeacherOtp: (...args: unknown[]) => mocks.verifyTeacherOtp(...args),
  },
}));

vi.mock("@stores/useAuthStore", () => ({
  useAuthStore: () => ({
    setTokens: mocks.setTokens,
    setUser: mocks.setUser,
  }),
}));

vi.mock("@hooks/useToast", () => ({
  useToast: () => ({ success: mocks.success, error: mocks.error }),
}));

import Login from "@pages/auth/Login";

function LocationOutput() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Login />
      <LocationOutput />
    </MemoryRouter>,
  );
}

describe("Login page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts Google authorization and navigates to the returned authorization URL", async () => {
    const user = userEvent.setup();
    mocks.googleAuthorize.mockResolvedValueOnce({
      authorize_url: "https://accounts.example.test/authorize?client=campus",
    });
    renderLogin();

    await user.click(screen.getByRole("button", { name: "Continue with Google" }));

    await waitFor(() => {
      expect(screen.getByTestId("location").textContent).toContain("google_authorize_url=");
    });
    expect(mocks.googleAuthorize).toHaveBeenCalledWith("init");
  });

  it("shows a user-facing error when Google authorization fails", async () => {
    const user = userEvent.setup();
    const failure = Object.assign(new Error("Request failed"), {
      campusvaultError: { message: "Authorization service unavailable" },
    });
    mocks.googleAuthorize.mockRejectedValueOnce(failure);
    renderLogin();

    await user.click(screen.getByRole("button", { name: "Continue with Google" }));

    await waitFor(() => {
      expect(mocks.error).toHaveBeenCalledWith(
        "Sign-in failed",
        "Authorization service unavailable",
      );
    });
  });
});
