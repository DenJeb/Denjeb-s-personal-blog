"""
========== 后台动态管理 ==========
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.models import Moment
from app.routers.admin.common import PAGE_SIZE, moment_page, page_slice
from app.services.interactions import (
    create_moment,
    delete_moment,
    update_moment,
    validate_moment_content,
)
from app.templating import templates

router = APIRouter()


@router.get("/moments")
def admin_moments(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Moment)) or 0
    page, total_pages = page_slice(page, total)
    moments = db.scalars(
        select(Moment)
        .order_by(Moment.created_at.desc(), Moment.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    moment_pages = {moment.id: moment_page(db, moment) for moment in moments}
    return templates.TemplateResponse(
        request=request,
        name="admin/moments.html",
        context={
            "app_name": settings.app_name,
            "moments": moments,
            "moment_pages": moment_pages,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.get("/moments/new")
def moment_create_page(request: Request, _admin: CurrentAdmin):
    return templates.TemplateResponse(
        request=request,
        name="admin/moment_form.html",
        context={
            "app_name": settings.app_name,
            "moment": None,
            "form": {"content": ""},
            "page": 1,
        },
    )


@router.post("/moments/new")
def moment_create(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    content: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    error = validate_moment_content(content)
    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/moment_form.html",
            context={
                "app_name": settings.app_name,
                "moment": None,
                "form": {"content": content},
                "error": error,
            },
            status_code=400,
        )

    create_moment(db, content)
    return RedirectResponse("/admin/moments?saved=1", status_code=303)


@router.get("/moments/{moment_id}/edit")
def moment_edit_page(
    request: Request,
    _admin: CurrentAdmin,
    moment_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/moment_form.html",
        context={
            "app_name": settings.app_name,
            "moment": moment,
            "form": {"content": moment.content},
            "page": page,
        },
    )


@router.post("/moments/{moment_id}/edit")
def moment_edit(
    request: Request,
    _admin: CurrentAdmin,
    moment_id: int,
    db: DbSession,
    content: str = Form(...),
    page: int = Query(1, ge=1),
    _csrf: None = Depends(verify_csrf),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    error = validate_moment_content(content)
    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/moment_form.html",
            context={
                "app_name": settings.app_name,
                "moment": moment,
                "form": {"content": content},
                "page": page,
                "error": error,
            },
            status_code=400,
        )

    update_moment(db, moment, content)
    suffix = f"&page={page}" if page > 1 else ""
    return RedirectResponse(f"/admin/moments?saved=1{suffix}", status_code=303)


@router.get("/moments/{moment_id}/delete")
def moment_delete_confirm(
    request: Request,
    _admin: CurrentAdmin,
    moment_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    page_suffix = f"?page={page}" if page > 1 else ""
    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": moment.content[:40],
            "item_type": "动态",
            "delete_url": f"/admin/moments/{moment.id}/delete{page_suffix}",
            "cancel_url": f"/admin/moments{page_suffix}",
        },
    )


@router.post("/moments/{moment_id}/delete")
def moment_delete(
    moment_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
    _csrf: None = Depends(verify_csrf),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    delete_moment(db, moment)
    suffix = f"&page={page}" if page > 1 else ""
    return RedirectResponse(f"/admin/moments?deleted=1{suffix}", status_code=303)
