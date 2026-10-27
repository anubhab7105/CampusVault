/** Library service — resource catalog reads + accounting. */
import { apiClient } from "@services/apiClient";
export const libraryService = {
    list: async (filters = {}) => {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value === undefined || value === null || value === "")
                return;
            params.set(key, String(value));
        });
        const { data } = await apiClient.get(`/library/resources?${params.toString()}`);
        return data.data;
    },
    get: async (id) => {
        const { data } = await apiClient.get(`/library/resources/${encodeURIComponent(id)}`);
        return data.data;
    },
    download: async (id) => {
        const { data } = await apiClient.post(`/library/resources/${encodeURIComponent(id)}/download`);
        return data.data;
    },
    create: async (payload) => {
        const { data } = await apiClient.post("/library/resources", payload);
        return data.data;
    },
    remove: async (id) => {
        const { data } = await apiClient.delete(`/library/resources/${encodeURIComponent(id)}`);
        return data;
    },
};
