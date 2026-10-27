import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Notifications placeholder — unread list + read receipts. */
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@stores/useAuthStore";
import { Card, Skeleton, EmptyState } from "@components/ui/index";
export default function Notifications() {
    const { user } = useAuthStore();
    const { data, isLoading } = useQuery({
        queryKey: ["notifications", "list"],
        queryFn: async () => {
            const res = await fetch("/api/v1/notifications", {
                headers: { Authorization: `Bearer ${useAuthStore.getState().access_token}` },
            });
            return res.json();
        },
        enabled: !!user,
    });
    if (isLoading) {
        return (_jsx("div", { className: "space-y-3", children: [1, 2, 3].map((i) => (_jsx(Card, { className: "h-20", children: _jsx(Skeleton, { className: "h-full w-full" }) }, i))) }));
    }
    const items = data?.items ?? [];
    if (items.length === 0) {
        return (_jsx("div", { className: "flex flex-col items-center justify-center py-20 text-center", children: _jsx(EmptyState, { title: "No notifications", description: "You're all caught up." }) }));
    }
    return (_jsxs("div", { className: "space-y-4", children: [_jsx("h1", { className: "text-heading-lg font-semibold text-ink-default", children: "Notifications" }), _jsx("div", { className: "space-y-3", children: items.map((n) => (_jsx(Card, { className: cn("border-l-4", n.is_read ? "" : "border-brand"), children: _jsxs("div", { className: "p-4", children: [_jsxs("div", { className: "flex items-start justify-between gap-2", children: [_jsx("h3", { className: "text-body-sm font-semibold text-ink-default", children: n.title }), _jsx("span", { className: `text-caption-xs ${n.is_read ? "text-ink-tertiary" : "text-brand font-medium"}`, children: n.is_read ? "Read" : "Unread" })] }), _jsx("p", { className: "mt-1 text-body-sm text-ink-secondary", children: n.body ?? "" }), _jsx("p", { className: "mt-2 text-caption-xs text-ink-tertiary", children: new Date(n.created_at).toLocaleString() })] }) }, n.id))) })] }));
}
