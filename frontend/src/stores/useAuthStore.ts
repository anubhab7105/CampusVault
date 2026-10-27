/** Zustand store — auth state + token persistence. */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { SignedInUser, User } from "@types/auth";
import { clearTokens, getTokens, setTokens } from "@utils/tokenStorage";

export const useAuthStore = create<SignedInUser & {
  isAuthenticated: boolean;
  loading: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User) => void;
  clear: () => void;
  logout: () => void;
}>()(
  persist(
    (set) => ({
      access_token: null,
      refresh_token: null,
      user: null,
      isAuthenticated: false,
      loading: false,

      setTokens: (access: string, refresh: string) => {
        setTokens(access, refresh);
        set({ access_token: access, refresh_token: refresh, isAuthenticated: true });
      },

      setUser: (user: User) => set({ user }),

      clear: () => {
        clearTokens();
        set({ access_token: null, refresh_token: null, user: null, isAuthenticated: false });
      },

      logout: () => {
        clearTokens();
        set({ access_token: null, refresh_token: null, user: null, isAuthenticated: false });
      },
    }),
    {
      name: STORAGE_KEYS.TOKENS,
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        access_token: state.access_token,
        refresh_token: state.refresh_token,
      }),
    },
  ),
);

import { STORAGE_KEYS } from "@constants/index";
