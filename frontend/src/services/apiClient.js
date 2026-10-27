/** Axios client with access-token refresh rotation. */
import axios from "axios";
import { useAuthStore } from "@stores/useAuthStore";
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
let refreshing = false;
let refreshPromise = null;
export const apiClient = axios.create({
    baseURL: API_BASE,
    headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
    },
});
apiClient.interceptors.request.use((config) => {
    const store = useAuthStore.getState();
    if (store.access_token) {
        config.headers.Authorization = `Bearer ${store.access_token}`;
    }
    return config;
});
let logoutTimer = null;
apiClient.interceptors.response.use((response) => response, async (error) => {
    const originalRequest = error.config;
    if (!originalRequest)
        return Promise.reject(error);
    const { response } = error;
    const status = response?.status;
    const store = useAuthStore.getState();
    // 401 on a refresh attempt → full logout.
    if (status === 401 && originalRequest.url?.endsWith("/auth/refresh")) {
        store.logout();
        return Promise.reject(error);
    }
    // 401 → try token rotation once.
    if (status === 401 && !originalRequest._retry && store.refresh_token) {
        originalRequest._retry = true;
        if (!refreshing) {
            refreshing = true;
            refreshPromise = rotateRefresh(store.refresh_token);
        }
        try {
            const newAccess = await refreshPromise;
            if (newAccess) {
                return apiClient(originalRequest);
            }
            store.logout();
        }
        finally {
            refreshing = false;
            refreshPromise = null;
        }
    }
    // Surf canonical CampusVault error envelope to callers.
    if (response?.data) {
        const envelope = response.data;
        error.campusvaultError = envelope.error ?? {
            code: "UNKNOWN_ERROR",
            message: String(envelope?.message ?? error.message),
        };
    }
    return Promise.reject(error);
});
async function rotateRefresh(refreshToken) {
    try {
        const { data } = await apiClient.post("/auth/refresh", {});
        if (data?.data) {
            const store = useAuthStore.getState();
            store.setTokens(data.data.access_token, data.data.refresh_token);
            return data.data.access_token;
        }
        return null;
    }
    catch {
        return null;
    }
}
export { logoutTimer };
