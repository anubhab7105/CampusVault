/** Notification service placeholder — wiring to /api/v1/notifications. */

import { apiClient } from "@services/apiClient";

export const notificationService = {
  list: async (params?: { unread?: boolean; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.unread) qs.set("unread", "true");
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { items: any[]; paging: any };
    }>(`/notifications?${qs.toString()}`);
    return data.data;
  },

  unreadCount: async () => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { count: number };
    }>("/notifications/unread-count");
    return data.data;
  },

  markRead: async (id: string) => {
    const { data } = await apiClient.post<{ success: boolean; message: string }>(
      `/notifications/${encodeURIComponent(id)}/read`
    );
    return data;
  },

  markAllRead: async () => {
    const { data } = await apiClient.post<{ success: boolean; message: string; data: { updated: number } }>(
      "/notifications/read-all"
    );
    return data.data;
  },
};
