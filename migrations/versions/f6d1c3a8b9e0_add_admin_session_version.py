"""add admin session version

Revision ID: f6d1c3a8b9e0
Revises: e5c9a2d4f6b8
Create Date: 2026-10-31 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6d1c3a8b9e0'
down_revision: Union[str, Sequence[str], None] = 'e5c9a2d4f6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'admin_users',
        sa.Column(
            'session_version',
            sa.Integer(),
            server_default=sa.text('0'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('admin_users', 'session_version')
