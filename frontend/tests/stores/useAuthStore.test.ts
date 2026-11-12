import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuthStore } from "@stores/useAuthStore";
import type { User } from "@/types/auth";

const user: User = {
  id: "user-1",
  email: "student@example.edu",
  full_name: "Test Student",
  auth_provider: "google",
  is_active: true,
  role: "Student",
};

describe("useAuthStore", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useAuthStore.getState().clear();
  });

  it("starts unauthenticated and exposes no user", async () => {
    vi.resetModules();
    sessionStorage.clear();
    const { useAuthStore: freshStore } = await import("@stores/useAuthStore");
    const initialState = freshStore.getState();
    expect(initialState).toMatchObject({
      access_token: null,
      refresh_token: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it("sets tokens and user after a successful sign in", () => {
    const store = useAuthStore.getState();
    store.setTokens("access-token", "refresh-token");
    store.setUser(user);

    expect(useAuthStore.getState()).toMatchObject({
      access_token: "access-token",
      refresh_token: "refresh-token",
      user,
      isAuthenticated: true,
    });
  });

  it("clears local authentication state on logout", async () => {
    useAuthStore.getState().setTokens("access-token", "refresh-token");
    useAuthStore.getState().setUser(user);

    await useAuthStore.getState().logout();

    expect(useAuthStore.getState()).toMatchObject({
      access_token: null,
      refresh_token: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it("persists only token state in session storage, not the user profile", () => {
    useAuthStore.getState().setTokens("access-token", "refresh-token");
    useAuthStore.getState().setUser(user);

    const persisted = JSON.parse(JSON.parse(sessionStorage.getItem("cv_tokens") ?? '"{}"'));
    expect(persisted.state).toEqual({
      access_token: "access-token",
      refresh_token: "refresh-token",
    });
    expect(persisted.state).not.toHaveProperty("user");
  });
});
