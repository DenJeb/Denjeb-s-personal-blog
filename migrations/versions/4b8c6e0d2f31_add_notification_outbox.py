"""add notification outbox

Revision ID: 4b8c6e0d2f31
Revises: 3a7b5d9c1e20
Create Date: 2026-11-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b8c6e0d2f31"
down_revision: Union[str, Sequence[str], None] = "3a7b5d9c1e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column(
            "attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_outbox_kind"),
        "notification_outbox",
        ["kind"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_outbox_created_at"),
        "notification_outbox",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_outbox_sent_at"),
        "notification_outbox",
        ["sent_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_notification_outbox_sent_at"), table_name="notification_outbox"
    )
    op.drop_index(
        op.f("ix_notification_outbox_created_at"), table_name="notification_outbox"
    )
    op.drop_index(
        op.f("ix_notification_outbox_kind"), table_name="notification_outbox"
    )
    op.drop_table("notification_outbox")
