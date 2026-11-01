"""add moments, moment comments, messages, and comment user id

Revision ID: b7f3c2d1e4a6
Revises: a3c5e7b9d1f2
Create Date: 2026-11-01 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3c2d1e4a6"
down_revision: Union[str, Sequence[str], None] = "a3c5e7b9d1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("comments") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_comments_user_id"), ["user_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_comments_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.create_table(
        "moments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_moments_created_at"), "moments", ["created_at"], unique=False
    )

    op.create_table(
        "moment_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("moment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("author_name", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "is_approved",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["moment_id"], ["moments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_moment_comments_moment_id"),
        "moment_comments",
        ["moment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_moment_comments_user_id"),
        "moment_comments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_moment_comments_is_approved"),
        "moment_comments",
        ["is_approved"],
        unique=False,
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_user_id"), "messages", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_messages_created_at"), "messages", ["created_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_messages_created_at"), table_name="messages")
    op.drop_index(op.f("ix_messages_user_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(
        op.f("ix_moment_comments_is_approved"), table_name="moment_comments"
    )
    op.drop_index(
        op.f("ix_moment_comments_user_id"), table_name="moment_comments"
    )
    op.drop_index(
        op.f("ix_moment_comments_moment_id"), table_name="moment_comments"
    )
    op.drop_table("moment_comments")

    op.drop_index(op.f("ix_moments_created_at"), table_name="moments")
    op.drop_table("moments")

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint(
            "fk_comments_user_id_users", type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_comments_user_id"))
        batch_op.drop_column("user_id")
