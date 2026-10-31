"""add blog post is_published

Revision ID: a3c5e7b9d1f2
Revises: f6d1c3a8b9e0
Create Date: 2026-10-31 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c5e7b9d1f2'
down_revision: Union[str, Sequence[str], None] = 'f6d1c3a8b9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'blog_posts',
        sa.Column(
            'is_published',
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f('ix_blog_posts_is_published'),
        'blog_posts',
        ['is_published'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_blog_posts_is_published'),
        table_name='blog_posts',
    )
    op.drop_column('blog_posts', 'is_published')
