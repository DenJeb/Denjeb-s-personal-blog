"""make message user id nullable

Revision ID: e1f2a3b4c5d6
Revises: d9e5f3a7b2c4
Create Date: 2026-11-01 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d9e5f3a7b2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM messages WHERE user_id IS NULL")
    ).scalar()
    if null_count:
        raise RuntimeError(
            "messages.user_id 存在 NULL 行，不能恢复为非空约束。"
        )
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
