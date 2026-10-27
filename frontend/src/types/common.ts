/** Shared primitive types used across the frontend. */

export type UUID = string;
export type RoleName = "Student" | "Teacher" | "Admin";

import type { UUID } from "./common";
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PagedResponse<T> {
  items: T[];
  paging: PaginationMeta;
}

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface SortDirection {
  field: string;
  order: "asc" | "desc";
}
