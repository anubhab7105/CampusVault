/** Notification + audit domain types. */

export type NotificationType =
  | "resource_shared"
  | "group_message"
  | "moderation"
  | "system";

export interface Notification {
  id: UUID;
  user_id: UUID;
  notification_type: NotificationType;
  title: string;
  body?: string | null;
  payload?: Record<string, unknown> | null;
  is_read: boolean;
  read_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
}

export interface AuditLog {
  id: UUID;
  actor_id?: UUID | null;
  action: string;
  entity_type: string;
  entity_id?: UUID | null;
  request_context?: Record<string, unknown> | null;
  changes?: Record<string, unknown> | null;
  created_at: string;
}

export interface Group {
  id: UUID;
  name: string;
  description?: string | null;
  group_type: string;
  owner_id: UUID;
  subject_id?: UUID | null;
  section_id?: UUID | null;
  is_active: boolean;
  created_at: string;
}

export interface Department {
  id: UUID;
  name: string;
  code: string;
  description?: string | null;
}

export interface Program {
  id: UUID;
  department_id: UUID;
  name: string;
  code: string;
  description?: string | null;
}

export interface Semester {
  id: UUID;
  program_id: UUID;
  number: number;
}

export interface Section {
  id: UUID;
  semester_id: UUID;
  name: string;
  capacity?: number | null;
}

export interface Subject {
  id: UUID;
  semester_id: UUID;
  name: string;
  code: string;
  credits?: number | null;
}
