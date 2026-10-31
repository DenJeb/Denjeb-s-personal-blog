"""
========== 后台分类管理 ==========
"""

import re

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Category, Note
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.templating import templates

router = APIRouter()

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
NAME_MAX_LENGTH = 100


def _category_rows(db) -> list[dict]:
    rows = db.execute(
        select(Category, func.count(Note.id))
        .outerjoin(Note, Note.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.id)
    ).all()
    return [{"category": category, "note_count": count} for category, count in rows]


def _validate_category(slug: str, name: str) -> tuple[str, str, str | None]:
    slug = slug.strip().lower()
    name = name.strip()

    error = None
    if SLUG_RE.fullmatch(slug) is None:
        error = "分类标识只能包含小写字母、数字、下划线和短横线，最长 50 个字符。"
    elif not name:
        error = "分类名称不能为空。"
    elif len(name) > NAME_MAX_LENGTH:
        error = f"分类名称不能超过 {NAME_MAX_LENGTH} 个字符。"

    return slug, name, error


def _conflicts(db, slug: str, name: str, exclude_id: int | None = None):
    condition = or_(Category.slug == slug, Category.name == name)
    if exclude_id is not None:
        condition = condition & (Category.id != exclude_id)
    return db.scalar(select(Category.id).where(condition)) is not None


@router.get("/categories")
def admin_categories(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    rows = _category_rows(db)
    total = len(rows)
    page, total_pages = page_slice(page, total)
    start = (page - 1) * PAGE_SIZE
    categories = rows[start : start + PAGE_SIZE]
    return templates.TemplateResponse(
        request=request,
        name="admin/categories.html",
        context={
            "app_name": settings.app_name,
            "categories": categories,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
            "in_use": request.query_params.get("in_use") == "1",
        },
    )


@router.get("/categories/new")
def category_create_page(request: Request, _admin: CurrentAdmin):
    return templates.TemplateResponse(
        request=request,
        name="admin/category_form.html",
        context={
            "app_name": settings.app_name,
            "category": None,
            "form": {"slug": "", "name": ""},
        },
    )


@router.post("/categories/new")
def category_create(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    slug: str = Form(...),
    name: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    slug, name, error = _validate_category(slug, name)
    if error is None and _conflicts(db, slug, name):
        error = "分类标识或名称已被使用。"

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/category_form.html",
            context={
                "app_name": settings.app_name,
                "category": None,
                "form": {"slug": slug, "name": name},
                "error": error,
            },
            status_code=400,
        )

    db.add(Category(slug=slug, name=name))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="admin/category_form.html",
            context={
                "app_name": settings.app_name,
                "category": None,
                "form": {"slug": slug, "name": name},
                "error": "分类标识或名称已被使用。",
            },
            status_code=400,
        )

    return RedirectResponse("/admin/categories?saved=1", status_code=303)


@router.get("/categories/{category_id}/edit")
def category_edit_page(
    request: Request,
    _admin: CurrentAdmin,
    category_id: int,
    db: DbSession,
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/category_form.html",
        context={
            "app_name": settings.app_name,
            "category": category,
            "form": {"slug": category.slug, "name": category.name},
        },
    )


@router.post("/categories/{category_id}/edit")
def category_edit(
    request: Request,
    _admin: CurrentAdmin,
    category_id: int,
    db: DbSession,
    slug: str = Form(...),
    name: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在！")

    slug, name, error = _validate_category(slug, name)
    if error is None and _conflicts(db, slug, name, exclude_id=category_id):
        error = "分类标识或名称已被使用。"

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/category_form.html",
            context={
                "app_name": settings.app_name,
                "category": category,
                "form": {"slug": slug, "name": name},
                "error": error,
            },
            status_code=400,
        )

    category.slug = slug
    category.name = name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="admin/category_form.html",
            context={
                "app_name": settings.app_name,
                "category": category,
                "form": {"slug": slug, "name": name},
                "error": "分类标识或名称已被使用。",
            },
            status_code=400,
        )

    return RedirectResponse("/admin/categories?saved=1", status_code=303)


@router.get("/categories/{category_id}/delete")
def category_delete_confirm(
    request: Request,
    _admin: CurrentAdmin,
    category_id: int,
    db: DbSession,
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": f"{category.name}（{category.slug}）",
            "item_type": "分类",
            "delete_url": f"/admin/categories/{category.id}/delete",
            "cancel_url": "/admin/categories",
        },
    )


@router.post("/categories/{category_id}/delete")
def category_delete(
    category_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在！")

    note_count = (
        db.scalar(
            select(func.count())
            .select_from(Note)
            .where(Note.category_id == category_id)
        )
        or 0
    )
    if note_count > 0:
        return RedirectResponse("/admin/categories?in_use=1", status_code=303)

    db.delete(category)
    db.commit()
    return RedirectResponse("/admin/categories?deleted=1", status_code=303)
