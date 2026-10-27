"""Message edit window enforcement.

 enforces that only the original sender may edit a message within a configurable
 window (default 15 minutes). After the window, only admins/owners may edit (via
 tombstone + re-post). The window length is configured via app config
 (MESSAGE_EDIT_WINDOW_MINUTES).

This migration adds no new columns/ tables — the edit-window logic is entirely
 server-enforced in ChatService.edit_group_message() and the corresponding
 frontend validation.
"""

from __future__ import annotations

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No schema changes; the edit-window rule is pure application logic.
    # The ChatService enforces the window by comparing message.created_at
    # against datetime.utcnow() - EDIT_WINDOW_MINUTES.
    pass


def downgrade() -> None:
    # No schema changes to revert.
    pass
