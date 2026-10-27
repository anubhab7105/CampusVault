/** Admin service placeholder — wiring to /api/v1/admin. */

import { apiClient } from "@services/apiClient";

export const adminService = {
  stats: async () => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { users: number; resources: number };
    }>("/admin/stats");
    return data.data;
  },

  users: async () => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { items: any[]; paging: any };
    }>("/admin/users");
    return data.data;
  },

  deactivate: async (id: string) => {
    const { data } = await apiClient.post<{ success: boolean; message: string }>(
      `/admin/users/${encodeURIComponent(id)}/deactivate`
    );
    return data;
  },
};
