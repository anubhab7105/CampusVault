/** Sidebar store — mobile-first collapse state. */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface SidebarState {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  toggle: () => void;
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      collapsed: false,

      setCollapsed: (collapsed) => set({ collapsed }),

      toggle: () => set((state) => ({ collapsed: !state.collapsed })),
    }),
    {
      name: "cv_sidebar_collapsed",
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
