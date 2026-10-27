import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/** Library placeholder — browse + download accounting. */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { libraryService } from "@services/libraryService";
import { useAuthStore } from "@stores/useAuthStore";
import { Card, Button, Skeleton, EmptyState } from "@components/ui/index";
import { PERMISSIONS } from "@constants/permissions";
import { hasPermission } from "@constants/permissions";
export default function Library() {
    const { user } = useAuthStore();
    const queryClient = useQueryClient();
    const { data, isLoading } = useQuery({
        queryKey: ["library", "resources"],
        queryFn: () => libraryService.list(),
        enabled: !!user,
    });
    const download = useMutation({
        mutationFn: libraryService.download,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library", "resources"] }),
    });
    if (isLoading) {
        return (_jsxs("div", { className: "space-y-4", children: [_jsx(Card, { className: "h-12", children: _jsx(Skeleton, { className: "h-full w-1/3" }) }), [1, 2, 3].map((i) => (_jsx(Card, { className: "h-40", children: _jsx(Skeleton, { className: "h-full w-full" }) }, i)))] }));
    }
    const items = data?.items ?? [];
    if (items.length === 0) {
        return (_jsx("div", { className: "flex flex-col items-center justify-center py-20 text-center", children: _jsx(EmptyState, { title: "No resources yet", description: "Ask your teacher to publish notes and past papers." }) }));
    }
    return (_jsxs("div", { className: "space-y-6", children: [_jsx("h1", { className: "text-heading-lg font-semibold text-ink-default", children: "Library" }), _jsx("div", { className: "grid grid-cols-1 md:grid-cols-3 gap-4", children: items.map((resource) => (_jsx(Card, { children: _jsxs("div", { className: "p-4", children: [_jsx("h3", { className: "text-body-md font-semibold text-ink-default", children: resource.title }), _jsxs("p", { className: "text-caption-xs text-ink-secondary mt-1", children: [resource.resource_type, " \u2022 ", resource.visibility] }), _jsxs("div", { className: "mt-4 flex items-center justify-between", children: [_jsxs("span", { className: "text-body-sm text-ink-secondary", children: ["Downloads: ", resource.download_count] }), _jsx(Button, { size: "sm", onClick: () => download.mutate(resource.id), disabled: !hasPermission(user?.role, [PERMISSIONS.LIBRARY_READ]), children: "Download" })] })] }) }, resource.id))) })] }));
}
