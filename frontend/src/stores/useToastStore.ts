/** Toast store — global non-blocking notifications. */

import { create } from "zustand";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: "default" | "destructive" | "success" | "warning";
  duration?: number;
}

export interface ToastState {
  toasts: Toast[];
  add: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
  clear: () => void;
}

let nextId = 0;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  add: (toast) => {
    const id = String(++nextId);
    set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
    if (toast.duration !== 0) {
      setTimeout(() => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })), toast.duration ?? 5000);
    }
  },

  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),

  clear: () => set({ toasts: [] }),
}));
