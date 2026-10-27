/** useToast hook — component-friendly toast API. */

import { useToastStore } from "@stores/useToastStore";
import type { ToastState } from "@stores/useToastStore";

export function useToast() {
  const { toasts, add, remove, clear } = useToastStore((state: ToastState) => ({
    toasts: state.toasts,
    add: state.add,
    remove: state.remove,
    clear: state.clear,
  }));

  return {
    toasts,
    toast: add,
    dismiss: remove,
    clear,
    success: (title: string, description?: string) =>
      add({ title, description, variant: "success" }),
    error: (title: string, description?: string) =>
      add({ title, description, variant: "destructive" }),
    warning: (title: string, description?: string) =>
      add({ title, description, variant: "warning" }),
  };
}
