/** Notifications placeholder — unread list + read receipts. */

import { useQuery } from "@tanstack/react-query";
import { notificationService } from "@services/notificationService"; // placeholder import
import { useAuthStore } from "@stores/useAuthStore";
import { Card, Button, Skeleton, EmptyState } from "@components/ui/index";

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
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="h-20"><Skeleton className="h-full w-full" /></Card>
        ))}
      </div>
    );
  }

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <EmptyState title="No notifications" description="You're all caught up." />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-heading-lg font-semibold text-ink-default">Notifications</h1>
      <div className="space-y-3">
        {items.map((n: any) => (
          <Card key={n.id} className={cn("border-l-4", n.is_read ? "" : "border-brand")}>
            <div className="p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-body-sm font-semibold text-ink-default">{n.title}</h3>
                <span className={`text-caption-xs ${n.is_read ? "text-ink-tertiary" : "text-brand font-medium"}`}>
                  {n.is_read ? "Read" : "Unread"}
                </span>
              </div>
              <p className="mt-1 text-body-sm text-ink-secondary">{n.body ?? ""}</p>
              <p className="mt-2 text-caption-xs text-ink-tertiary">{new Date(n.created_at).toLocaleString()}</p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
