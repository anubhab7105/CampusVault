/** Library service — resource catalog reads + accounting. */

import { apiClient } from "@services/apiClient";
import type { Resource, ResourceListFilters } from "@/types/library";

export const libraryService = {
  list: async (filters: ResourceListFilters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") return;
      params.set(key, String(value));
    });
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: { items: Resource[]; paging: any };
    }>(`/library/resources?${params.toString()}`);
    return data.data;
  },

  get: async (id: string) => {
    const { data } = await apiClient.get<{
      success: boolean;
      message: string;
      data: Resource;
    }>(`/library/resources/${encodeURIComponent(id)}`);
    return data.data;
  },

  download: async (id: string) => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { file_id: string | null; external_url: string | null };
    }>(`/library/resources/${encodeURIComponent(id)}/download`);
    return data.data;
  },

  create: async (payload: {
    subject_id: string;
    title: string;
    description?: string;
    resource_type: string;
    visibility?: string;
    file_id?: string | null;
    external_url?: string | null;
  }) => {
    const { data } = await apiClient.post<{
      success: boolean;
      message: string;
      data: { id: string };
    }>("/library/resources", payload);
    return data.data;
  },

  remove: async (id: string) => {
    const { data } = await apiClient.delete<{
      success: boolean;
      message: string;
    }>(`/library/resources/${encodeURIComponent(id)}`);
    return data;
  },
};
