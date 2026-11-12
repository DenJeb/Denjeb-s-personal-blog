"""add post updated_at

Revision ID: c7a1f2b3d4e5
Revises: 4b8c6e0d2f31
Create Date: 2026-11-12 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7a1f2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "4b8c6e0d2f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "blog_posts",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("blog_posts", "updated_at")
