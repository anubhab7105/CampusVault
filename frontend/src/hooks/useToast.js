/** useToast hook — component-friendly toast API. */
import { useToastStore } from "@stores/useToastStore";
export function useToast() {
    const { toasts, add, remove, clear } = useToastStore((state) => ({
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
        success: (title, description) => add({ title, description, variant: "success" }),
        error: (title, description) => add({ title, description, variant: "destructive" }),
        warning: (title, description) => add({ title, description, variant: "warning" }),
    };
}
