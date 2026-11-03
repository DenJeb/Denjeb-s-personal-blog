"""add admin totp secret

Revision ID: 3a7b5d9c1e20
Revises: 2f8a4c1d6b90
Create Date: 2026-11-03 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a7b5d9c1e20"
down_revision: Union[str, Sequence[str], None] = "2f8a4c1d6b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("totp_secret", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.drop_column("totp_secret")
