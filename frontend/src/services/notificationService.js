/** Notification service placeholder — wiring to /api/v1/notifications. */
import { apiClient } from "@services/apiClient";
export const notificationService = {
    list: async (params) => {
        const qs = new URLSearchParams();
        if (params?.unread)
            qs.set("unread", "true");
        if (params?.page)
            qs.set("page", String(params.page));
        if (params?.page_size)
            qs.set("page_size", String(params.page_size));
        const { data } = await apiClient.get(`/notifications?${qs.toString()}`);
        return data.data;
    },
    unreadCount: async () => {
        const { data } = await apiClient.get("/notifications/unread-count");
        return data.data;
    },
    markRead: async (id) => {
        const { data } = await apiClient.post(`/notifications/${encodeURIComponent(id)}/read`);
        return data;
    },
    markAllRead: async () => {
        const { data } = await apiClient.post("/notifications/read-all");
        return data.data;
    },
};
