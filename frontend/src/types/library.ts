/** Library / resource domain types. */

export type ResourceType =
  | "note"
  | "book"
  | "past_paper"
  | "slide"
  | "link";

export type Visibility = "section" | "subject" | "department" | "college" | "private";

export interface Resource {
  id: UUID;
  subject_id: UUID;
  file_id?: UUID | null;
  uploaded_by: UUID;
  title: string;
  description?: string | null;
  resource_type: ResourceType;
  visibility: Visibility;
  external_url?: string | null;
  share_token?: string | null;
  is_published: boolean;
  download_count: number;
  view_count: number;
  created_at: string;
  updated_at: string;
}

export interface FileRecord {
  id: UUID;
  uploader_id: UUID;
  subject_id?: UUID | null;
  original_filename: string;
  storage_key: string;
  bucket: string;
  mime_type: string;
  file_size: number;
  sha256_checksum?: string | null;
  scan_status: "pending" | "clean" | "infected" | "failed";
  scanned_at?: string | null;
  created_at: string;
}

export interface ResourceListFilters {
  department_id?: UUID;
  program_id?: UUID;
  semester_id?: UUID;
  section_id?: UUID;
  subject_id?: UUID;
  resource_type?: ResourceType;
  visibility?: Visibility;
  q?: string;
  sort?: "created_at" | "title" | "download_count";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
