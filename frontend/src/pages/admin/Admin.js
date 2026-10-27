import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Admin placeholder — role-gated stats + user list. */
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@stores/useAuthStore";
import { Card, Button, EmptyState } from "@components/ui/index";
import { PERMISSIONS } from "@constants/permissions";
import { hasPermission } from "@constants/permissions";
export default function Admin() {
    const { user } = useAuthStore();
    const allowed = hasPermission(user?.role, [PERMISSIONS.ADMIN_DASHBOARD_VIEW]);
    if (!allowed) {
        return (_jsx("div", { className: "flex flex-col items-center justify-center py-20 text-center", children: _jsx(EmptyState, { title: "Admin access required", description: "Your role does not include admin:dashboard:view.", action: _jsx(Button, { variant: "outline", size: "sm", children: "Back to dashboard" }) }) }));
    }
    const { data, isLoading } = useQuery({
        queryKey: ["admin", "stats"],
        queryFn: async () => {
            const res = await fetch("/api/v1/admin/stats", {
                headers: { Authorization: `Bearer ${useAuthStore.getState().access_token}` },
            });
            return res.json();
        },
        enabled: !!user,
    });
    return (_jsxs("div", { className: "space-y-6", children: [_jsx("h1", { className: "text-heading-lg font-semibold text-ink-default", children: "Admin Console" }), isLoading ? (_jsx(Card, { className: "h-64", children: _jsx(SkeletonCard, {}) })) : (_jsxs("div", { className: "grid grid-cols-1 md:grid-cols-3 gap-6", children: [_jsx(Card, { children: _jsxs("div", { className: "p-4", children: [_jsx("h3", { className: "text-body-sm font-medium text-ink-secondary", children: "Users" }), _jsx("p", { className: "text-3xl font-bold text-ink-default", children: data?.users ?? "—" })] }) }), _jsx(Card, { children: _jsxs("div", { className: "p-4", children: [_jsx("h3", { className: "text-body-sm font-medium text-ink-secondary", children: "Resources" }), _jsx("p", { className: "text-3xl font-bold text-ink-default", children: data?.resources ?? "—" })] }) })] })), _jsx(Card, { children: _jsx("div", { className: "p-4", children: _jsx("div", { className: "text-caption-xs text-ink-secondary", children: "User directory placeholder \u2014 wired to /api/v1/admin/users." }) }) })] }));
}
function SkeletonCard() {
    return (_jsxs("div", { className: "p-4", children: [_jsx("div", { className: "h-8 w-48 bg-surface-200 rounded animate-pulse" }), _jsx("div", { className: "mt-4 h-8 w-32 bg-surface-200 rounded animate-pulse" })] }));
}
