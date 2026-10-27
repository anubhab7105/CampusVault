/** Zustand store — auth state + token persistence (session-scoped). */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { STORAGE_KEYS } from "@constants/index";
const TOKEN_STORAGE_KEY = STORAGE_KEYS.TOKENS;
const storage = {
    getItem: (name) => {
        try {
            const raw = sessionStorage.getItem(name);
            return raw ? JSON.parse(raw) : null;
        }
        catch {
            return null;
        }
    },
    setItem: (name, value) => {
        try {
            sessionStorage.setItem(name, JSON.stringify(value));
        }
        catch {
            /* storage quota exceeded — ignore gracefully */
        }
    },
    removeItem: (name) => {
        try {
            sessionStorage.removeItem(name);
        }
        catch {
            /* ignore */
        }
    },
};
export const useAuthStore = create()(persist((set) => ({
    access_token: null,
    refresh_token: null,
    user: null,
    isAuthenticated: false,
    loading: false,
    setTokens: (access, refresh) => set({ access_token: access, refresh_token: refresh, isAuthenticated: true }),
    setUser: (user) => set({ user }),
    logout: () => set({ access_token: null, refresh_token: null, user: null, isAuthenticated: false }),
}), {
    name: TOKEN_STORAGE_KEY,
    storage: createJSONStorage(() => storage),
    partialize: (state) => ({
        access_token: state.access_token,
        refresh_token: state.refresh_token,
    }),
}));
