"""DM pair normalization: unique constraint on (least(user_a, user_b), greatest(user_a, user_b)).

Ensures exactly one canonical DirectMessageConversation per unordered user pair.
The application layer (ConversationRepository.find_direct_between) enforces the
business rule. A PostgreSQL partial unique index is used when available; SQLite
relays on repository-level checks.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: partial unique index conversation_type = 'direct'
    # SQLite: no partial index support — enforced by repository logic only.
    op.create_index(
        "uq_conversations_direct_pair",
        "conversations",
        ["conversation_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_conversations_direct_pair", table_name="conversations")
