"""
========== 后台笔记管理 ==========
"""

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Category, Note
from app.routers.admin.common import (
    PAGE_SIZE,
    delete_unreferenced_uploads,
    fill_note,
    note_form_values,
    page_slice,
    upload_urls_in_text,
    validate_content_fields,
)
from app.templating import templates

router = APIRouter()


@router.get("/notes")
def admin_notes(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Note)) or 0
    page, total_pages = page_slice(page, total)
    notes = db.scalars(
        select(Note)
        .options(selectinload(Note.category))
        .order_by(Note.published_at.desc(), Note.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/notes.html",
        context={
            "app_name": settings.app_name,
            "notes": notes,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.get("/notes/{note_id}/edit")
def note_edit_page(request: Request, _admin: CurrentAdmin, note_id: int, db: DbSession):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在！")

    categories = db.scalars(select(Category).order_by(Category.id)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/note_form.html",
        context={
            "app_name": settings.app_name,
            "note": note,
            "form": note_form_values(note),
            "categories": categories,
        },
    )


@router.post("/notes/{note_id}/edit")
def note_edit(
    request: Request,
    _admin: CurrentAdmin,
    note_id: int,
    db: DbSession,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    published_at: str = Form(...),
    tags: str = Form(""),
    category_id: int = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在！")

    categories = db.scalars(select(Category).order_by(Category.id)).all()
    form = {
        "title": title,
        "summary": summary,
        "content": content,
        "published_at": published_at,
        "tags": tags,
        "category_id": category_id,
    }

    error, published_date = validate_content_fields(
        title, summary, content, published_at
    )
    if db.get(Category, category_id) is None:
        error = "分类不存在。"

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/note_form.html",
            context={
                "app_name": settings.app_name,
                "note": note,
                "form": form,
                "categories": categories,
                "error": error,
            },
            status_code=400,
        )

    assert published_date is not None
    old_urls = upload_urls_in_text(note.content, note.content_html)
    fill_note(note, title, summary, content, published_date, tags, category_id)
    db.commit()
    delete_unreferenced_uploads(db, old_urls)

    return RedirectResponse("/admin/notes?saved=1", status_code=303)


@router.get("/notes/new")
def note_create_page(request: Request, _admin: CurrentAdmin, db: DbSession):
    categories = db.scalars(select(Category).order_by(Category.id)).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/note_form.html",
        context={
            "app_name": settings.app_name,
            "note": None,
            "form": {
                "title": "",
                "summary": "",
                "content": "",
                "published_at": date.today().isoformat(),
                "tags": "",
                "category_id": categories[0].id if categories else 0,
            },
            "categories": categories,
        },
    )


@router.post("/notes/new")
def note_create(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    published_at: str = Form(...),
    tags: str = Form(""),
    category_id: int = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    categories = db.scalars(select(Category).order_by(Category.id)).all()
    form = {
        "title": title,
        "summary": summary,
        "content": content,
        "published_at": published_at,
        "tags": tags,
        "category_id": category_id,
    }

    error, published_date = validate_content_fields(
        title, summary, content, published_at
    )
    if db.get(Category, category_id) is None:
        error = "分类不存在。"

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/note_form.html",
            context={
                "app_name": settings.app_name,
                "note": None,
                "form": form,
                "categories": categories,
                "error": error,
            },
            status_code=400,
        )

    assert published_date is not None
    note = Note()
    fill_note(note, title, summary, content, published_date, tags, category_id)
    db.add(note)
    db.commit()

    return RedirectResponse("/admin/notes?saved=1", status_code=303)


@router.get("/notes/{note_id}/delete")
def note_delete_confirm(
    request: Request, _admin: CurrentAdmin, note_id: int, db: DbSession
):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": note.title,
            "item_type": "笔记",
            "delete_url": f"/admin/notes/{note.id}/delete",
            "cancel_url": "/admin/notes",
        },
    )


@router.post("/notes/{note_id}/delete")
def note_delete(
    note_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="笔记不存在！")

    candidates = upload_urls_in_text(note.content, note.content_html)
    db.delete(note)
    db.commit()
    delete_unreferenced_uploads(db, candidates)
    return RedirectResponse("/admin/notes?deleted=1", status_code=303)
