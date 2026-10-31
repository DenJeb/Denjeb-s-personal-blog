"""
========== 后台分类管理测试 ==========
"""

from datetime import date

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Category, Note
from tests.utils import csrf_token

SLUG = "pytest-cat-tmp"
NAME = "__pytest_category__"
NOTE_TITLE = "__pytest_cat_note__"


def _cleanup() -> None:
    with SessionLocal() as db:
        db.execute(delete(Note).where(Note.title.like(NOTE_TITLE + "%")))
        db.execute(delete(Category).where(Category.slug == SLUG))
        db.commit()


def test_category_crud(admin_client):
    _cleanup()
    try:
        assert admin_client.get("/admin/categories").status_code == 200

        token = csrf_token(admin_client.get("/admin/categories/new").text)
        response = admin_client.post(
            "/admin/categories/new",
            data={"csrf_token": token, "slug": SLUG, "name": NAME},
            follow_redirects=False,
        )
        assert response.status_code == 303

        with SessionLocal() as db:
            category = db.scalar(select(Category).where(Category.slug == SLUG))
            assert category is not None
            category_id = category.id

        page = admin_client.get(f"/admin/categories/{category_id}/edit")
        assert page.status_code == 200
        assert NAME in page.text

        token = csrf_token(page.text)
        response = admin_client.post(
            f"/admin/categories/{category_id}/edit",
            data={
                "csrf_token": token,
                "slug": SLUG,
                "name": NAME + "_edited",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        note_form = admin_client.get("/admin/notes/new")
        assert NAME + "_edited" in note_form.text

        token = csrf_token(
            admin_client.get(f"/admin/categories/{category_id}/delete").text
        )
        response = admin_client.post(
            f"/admin/categories/{category_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        with SessionLocal() as db:
            assert db.get(Category, category_id) is None
    finally:
        _cleanup()


def test_category_in_use_cannot_delete(admin_client):
    _cleanup()
    try:
        with SessionLocal() as db:
            category = Category(slug=SLUG, name=NAME)
            db.add(category)
            db.flush()
            category_id = category.id
            db.add(
                Note(
                    title=NOTE_TITLE,
                    summary="",
                    content="正文",
                    content_html="<p>正文</p>",
                    published_at=date(2026, 1, 1),
                    tags=[],
                    category_id=category_id,
                )
            )
            db.commit()

        token = csrf_token(
            admin_client.get(f"/admin/categories/{category_id}/delete").text
        )
        response = admin_client.post(
            f"/admin/categories/{category_id}/delete",
            data={"csrf_token": token},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "in_use=1" in response.headers["location"]

        with SessionLocal() as db:
            assert db.get(Category, category_id) is not None
    finally:
        _cleanup()
