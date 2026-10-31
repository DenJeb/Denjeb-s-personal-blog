"""add verification codes, email registration blocks and session version

Revision ID: 7b2e9d4c1a6f
Revises: 30a32dedc33c
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b2e9d4c1a6f'
down_revision: Union[str, Sequence[str], None] = '30a32dedc33c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'session_version',
            sa.Integer(),
            server_default=sa.text('0'),
            nullable=False,
        ),
    )

    op.create_table(
        'verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column(
            'attempts', sa.Integer(), server_default=sa.text('0'), nullable=False
        ),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_verification_codes_email'),
        'verification_codes',
        ['email'],
        unique=False,
    )
    op.create_index(
        op.f('ix_verification_codes_purpose'),
        'verification_codes',
        ['purpose'],
        unique=False,
    )
    op.create_index(
        op.f('ix_verification_codes_expires_at'),
        'verification_codes',
        ['expires_at'],
        unique=False,
    )

    op.create_table(
        'email_registration_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('blocked_until', sa.DateTime(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_email_registration_blocks_email'),
        'email_registration_blocks',
        ['email'],
        unique=True,
    )
    op.create_index(
        op.f('ix_email_registration_blocks_blocked_until'),
        'email_registration_blocks',
        ['blocked_until'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_email_registration_blocks_blocked_until'),
        table_name='email_registration_blocks',
    )
    op.drop_index(
        op.f('ix_email_registration_blocks_email'),
        table_name='email_registration_blocks',
    )
    op.drop_table('email_registration_blocks')

    op.drop_index(
        op.f('ix_verification_codes_expires_at'),
        table_name='verification_codes',
    )
    op.drop_index(
        op.f('ix_verification_codes_purpose'),
        table_name='verification_codes',
    )
    op.drop_index(
        op.f('ix_verification_codes_email'),
        table_name='verification_codes',
    )
    op.drop_table('verification_codes')

    op.drop_column('users', 'session_version')
