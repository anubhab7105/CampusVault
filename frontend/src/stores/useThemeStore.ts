/** Theme store — dark mode persistence via localStorage + data attribute. */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface ThemeState {
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "light",

      setTheme: (theme) => {
        document.documentElement.setAttribute("data-theme", theme);
        set({ theme });
      },

      toggleTheme: () =>
        set((state) => {
          const next = state.theme === "light" ? "dark" : "light";
          document.documentElement.setAttribute("data-theme", next);
          return { theme: next };
        }),
    }),
    {
      name: "cv_theme",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
