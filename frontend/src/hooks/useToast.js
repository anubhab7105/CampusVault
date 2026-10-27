/** useToast hook — component-friendly toast API. */
import { useToastStore } from "@stores/useToastStore";
export function useToast() {
    const toasts = useToastStore((state) => state.toasts);
    const add = useToastStore((state) => state.add);
    const remove = useToastStore((state) => state.remove);
    const clear = useToastStore((state) => state.clear);
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
