/** usePermission — hook driven by /auth/me that returns permission state. */

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@stores/useAuthStore";

export function usePermission(code: string) {
  const { user } = useAuthStore();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["auth", "me", "permissions", code],
    queryFn: async () => {
      const res = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${useAuthStore.getState().access_token}` },
      });
      const json = await res.json();
      if (!json.success || !json.data) {
        return { hasPermission: false, permissions: [] };
      }
      return { hasPermission: json.data.permissions.includes(code), permissions: json.data.permissions };
    },
    enabled: !!user && !!useAuthStore.getState().access_token,
  });

  return {
    hasPermission: data?.hasPermission ?? false,
    permissions: data?.permissions ?? [],
    loading: isLoading || !data,
    refetch,
  };
}
