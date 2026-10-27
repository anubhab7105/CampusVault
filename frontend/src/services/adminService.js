/** Admin service placeholder — wiring to /api/v1/admin. */
import { apiClient } from "@services/apiClient";
export const adminService = {
    stats: async () => {
        const { data } = await apiClient.get("/admin/stats");
        return data.data;
    },
    users: async () => {
        const { data } = await apiClient.get("/admin/users");
        return data.data;
    },
    deactivate: async (id) => {
        const { data } = await apiClient.post(`/admin/users/${encodeURIComponent(id)}/deactivate`);
        return data;
    },
};
