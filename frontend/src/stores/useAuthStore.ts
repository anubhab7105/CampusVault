/** Zustand store — auth state + token persistence (session-scoped). */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { User } from "@types/auth";
import { STORAGE_KEYS } from "@constants/index";

const TOKEN_STORAGE_KEY = STORAGE_KEYS.TOKENS;

const storage = {
  getItem: (name: string) => {
    try {
      const raw = sessionStorage.getItem(name);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  setItem: (name: string, value: unknown) => {
    try {
      sessionStorage.setItem(name, JSON.stringify(value));
    } catch {
      /* storage quota exceeded — ignore gracefully */
    }
  },
  removeItem: (name: string) => {
    try {
      sessionStorage.removeItem(name);
    } catch {
      /* ignore */
    }
  },
};

export interface AuthStoreState {
  access_token: string | null;
  refresh_token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStoreState>()(
  persist(
    (set) => ({
      access_token: null,
      refresh_token: null,
      user: null,
      isAuthenticated: false,
      loading: false,

      setTokens: (access: string, refresh: string) =>
        set({ access_token: access, refresh_token: refresh, isAuthenticated: true }),

      setUser: (user: User) => set({ user }),

      logout: () => set({ access_token: null, refresh_token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: TOKEN_STORAGE_KEY,
      storage: createJSONStorage(() => storage),
      partialize: (state) => ({
        access_token: state.access_token,
        refresh_token: state.refresh_token,
      }),
    },
  ),
);
