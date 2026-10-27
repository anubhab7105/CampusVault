/** Admin placeholder — role-gated stats + user list. */

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@stores/useAuthStore";
import { Card, Button, EmptyState } from "@components/ui/index";
import { PERMISSIONS } from "@constants/permissions";
import { hasPermission } from "@constants/permissions";

export default function Admin() {
  const { user } = useAuthStore();
  const allowed = hasPermission(user?.role, [PERMISSIONS.ADMIN_DASHBOARD_VIEW]);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/stats", {
        headers: { Authorization: `Bearer ${useAuthStore.getState().access_token}` },
      });
      return res.json();
    },
    enabled: allowed && !!user,
  });

  if (!allowed) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <EmptyState
          title="Admin access required"
          description="Your role does not include admin:dashboard:view."
          action={<Button variant="outline" size="sm">Back to dashboard</Button>}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-heading-lg font-semibold text-ink-default">Admin Console</h1>
      {isLoading ? (
        <Card className="h-64"><SkeletonCard /></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div className="p-4">
              <h3 className="text-body-sm font-medium text-ink-secondary">Users</h3>
              <p className="text-3xl font-bold text-ink-default">{data?.users ?? "—"}</p>
            </div>
          </Card>
          <Card>
            <div className="p-4">
              <h3 className="text-body-sm font-medium text-ink-secondary">Resources</h3>
              <p className="text-3xl font-bold text-ink-default">{data?.resources ?? "—"}</p>
            </div>
          </Card>
        </div>
      )}
      <Card>
        <div className="p-4">
          <div className="text-caption-xs text-ink-secondary">User directory placeholder — wired to /api/v1/admin/users.</div>
        </div>
      </Card>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="p-4">
      <div className="h-8 w-48 bg-surface-200 rounded animate-pulse" />
      <div className="mt-4 h-8 w-32 bg-surface-200 rounded animate-pulse" />
    </div>
  );
}
