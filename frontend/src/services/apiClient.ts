/** Axios client with access-token refresh rotation. */

import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@stores/useAuthStore";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

let refreshing = false;
let refreshPromise: Promise<string | null> | null = null;

export interface CampusVaultError {
  code: string;
  message: string;
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export const apiClient: AxiosInstance = axios.create({
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

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig;
    if (!originalRequest) return Promise.reject(error);

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
        refreshPromise = rotateRefresh();
      }
      try {
        const newAccess = await refreshPromise;
        if (newAccess) {
          return apiClient(originalRequest);
        }
        store.logout();
      } finally {
        refreshing = false;
        refreshPromise = null;
      }
    }

    // Surf canonical CampusVault error envelope to callers.
    if (response?.data) {
      const envelope = response.data as {
        success?: boolean;
        error?: CampusVaultError;
        message?: string;
      };
      (error as AxiosError & { campusvaultError?: CampusVaultError }).campusvaultError =
        envelope.error ?? { code: "UNKNOWN_ERROR", message: String(envelope?.message ?? error.message) };
    }
    return Promise.reject(error);
  },
);

async function rotateRefresh(): Promise<string | null> {
  try {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { access_token: string; refresh_token: string };
    }>("/auth/refresh", {});
    if (data?.data) {
      const store = useAuthStore.getState();
      store.setTokens(data.data.access_token, data.data.refresh_token);
      return data.data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}
