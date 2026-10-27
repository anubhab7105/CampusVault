/** Chat domain types. */

export type ConversationType = "group" | "direct";
export type MessageType = "text" | "file" | "system";

export interface Conversation {
  id: UUID;
  conversation_type: ConversationType;
  group_id?: UUID | null;
  created_by?: UUID | null;
  last_message_at?: string | null;
  is_active: boolean;
}

export interface Message {
  id: UUID;
  conversation_id: UUID;
  sender_id: UUID | null;
  message_type: MessageType;
  content?: string | null;
  file_id?: UUID | null;
  reply_to_id?: UUID | null;
  is_edited: boolean;
  edited_at?: string | null;
  delivered_at?: string | null;
  created_at: string;
}

export interface SocketAuthPayload {
  token: string;
}

export type SocketEvent =
  | "connect"
  | "disconnect"
  | "join_group"
  | "leave_group"
  | "send_group_message"
  | "edit_group_message"
  | "delete_group_message"
  | "typing"
  | "notification"
  | "read_receipt"
  | "delivery_status"
  | "socket_error";

export interface RoomMembership {
  conversation_id: UUID;
  user_id: UUID;
  joined_at: string;
  is_admin: boolean;
  last_read_at?: string | null;
}

export interface Presence {
  userId: UUID;
  online: boolean;
}
