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
    queryFn: libraryService.list,
    enabled: !!user,
  });

  const download = useMutation({
    mutationFn: libraryService.download,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["library", "resources"] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Card className="h-12"><Skeleton className="h-full w-1/3" /></Card>
        {[1, 2, 3].map((i) => (
          <Card key={i} className="h-40"><Skeleton className="h-full w-full" /></Card>
        ))}
      </div>
    );
  }

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <EmptyState title="No resources yet" description="Ask your teacher to publish notes and past papers." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-heading-lg font-semibold text-ink-default">Library</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {items.map((resource) => (
          <Card key={resource.id}>
            <div className="p-4">
              <h3 className="text-body-md font-semibold text-ink-default">{resource.title}</h3>
              <p className="text-caption-xs text-ink-secondary mt-1">
                {resource.resource_type} • {resource.visibility}
              </p>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-body-sm text-ink-secondary">Downloads: {resource.download_count}</span>
                <Button
                  size="sm"
                  onClick={() => download.mutate(resource.id)}
                  disabled={!hasPermission(user?.role, [PERMISSIONS.LIBRARY_READ])}
                >
                  Download
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
