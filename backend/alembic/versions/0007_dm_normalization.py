"""DM pair normalization: unique constraint on (least(user_a, user_b), greatest(user_a, user_b)).

Ensures exactly one canonical DirectMessageConversation per unordered user pair.
The actual constraint is a partial unique index; the ORM layer (ConversationRepository.find_direct_between)
enforces the business rule.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_conversations_direct_pair",
        "conversations",
        [],
        unique=True,
        postgresql_where=sa.text(
            "conversation_type = 'direct'"  # type: ignore[arg-type]  # noqa: E501
        ),
    )
    # SQLite does not support partial indexes; the uniqueness is enforced by the
    # ConversationRepository.find_direct_between() logic instead.


def downgrade() -> None:
    op.drop_index("uq_conversations_direct_pair", table_name="conversations")