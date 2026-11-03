"""add post slugs and heading anchors

Revision ID: 2f8a4c1d6b90
Revises: e1f2a3b4c5d6
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f8a4c1d6b90"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=200), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_blog_posts_slug"), ["slug"], unique=True
        )

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM blog_posts ORDER BY id")).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE blog_posts SET slug = :slug WHERE id = :id"),
            {"slug": f"post-{row.id}", "id": row.id},
        )

    try:
        from app.markdown import render_markdown_with_toc
    except ImportError:
        render_markdown_with_toc = None

    if render_markdown_with_toc is not None:
        posts = connection.execute(
            sa.text("SELECT id, content FROM blog_posts")
        ).fetchall()
        for post in posts:
            html, _ = render_markdown_with_toc(post.content)
            connection.execute(
                sa.text("UPDATE blog_posts SET content_html = :html WHERE id = :id"),
                {"html": html, "id": post.id},
            )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("blog_posts") as batch_op:
        batch_op.drop_index(batch_op.f("ix_blog_posts_slug"))
        batch_op.drop_column("slug")
