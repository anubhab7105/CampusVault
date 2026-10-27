
# Database Guide

## Database

Supabase PostgreSQL

## Standards

- UUID primary keys
- Foreign keys
- Composite indexes
- Soft delete where required
- Transactions
- Alembic migrations

## Initial Core Tables

- users
- roles
- permissions
- user_roles
- departments
- programs
- semesters
- sections
- subjects
- groups
- conversation_participants
- messages
- conversations
- files
- resources
- notifications
- audit_logs
- quota_usage
- notification_preferences

## Future Improvements

- Full-text search
- Materialized views
- Analytics tables
- Archival strategy

## Phase 4 Additions

- **Direct message normalization**: unique conversation per user pair, enforced by
  `uq_conversations_direct_pair` index on `conversations(conversation_type)` +
  application-layer checks in `ConversationRepository.find_direct_between()`.
- **Message edit window**: 15-minute server-enforced window; after expiry only
  admins may tombstone. Logic in `ChatService.edit_message()`.
- **Message tombstone**: soft delete via `Message.soft_delete()` / `wipe_content()`;
  content replaced with system message type, audit trail preserved.
- **Notification preferences**: per-user `notification_preferences` table controlling
  email/push/in-app alerts and digest frequency.
- **Quota tracking**: `quota_usage` table tracking per-user uploads per session,
  with reset interval configured via env vars.
