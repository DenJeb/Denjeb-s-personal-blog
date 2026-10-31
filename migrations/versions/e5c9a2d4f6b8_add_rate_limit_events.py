"""add rate limit events

Revision ID: e5c9a2d4f6b8
Revises: 7b2e9d4c1a6f
Create Date: 2026-10-31 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5c9a2d4f6b8'
down_revision: Union[str, Sequence[str], None] = '7b2e9d4c1a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'rate_limit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bucket', sa.String(length=100), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_rate_limit_events_bucket'),
        'rate_limit_events',
        ['bucket'],
        unique=False,
    )
    op.create_index(
        op.f('ix_rate_limit_events_created_at'),
        'rate_limit_events',
        ['created_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_rate_limit_events_created_at'),
        table_name='rate_limit_events',
    )
    op.drop_index(
        op.f('ix_rate_limit_events_bucket'),
        table_name='rate_limit_events',
    )
    op.drop_table('rate_limit_events')
