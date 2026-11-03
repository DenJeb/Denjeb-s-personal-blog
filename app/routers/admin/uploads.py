"""
========== 后台图片管理 ==========
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.routers.admin.common import PAGE_SIZE, page_slice
from app.services.uploads import UPLOAD_DIR, all_referenced_upload_urls
from app.templating import templates

router = APIRouter()


@router.get("/uploads")
def admin_uploads(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    referenced = all_referenced_upload_urls(db)
    files = []
    if UPLOAD_DIR.exists():
        for path in sorted(UPLOAD_DIR.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(UPLOAD_DIR).as_posix()
            url = f"/static/uploads/{relative}"
            files.append(
                {
                    "name": relative,
                    "url": url,
                    "size": path.stat().st_size,
                    "referenced": url in referenced,
                }
            )

    total = len(files)
    page, total_pages = page_slice(page, total)
    start = (page - 1) * PAGE_SIZE
    files = files[start : start + PAGE_SIZE]

    return templates.TemplateResponse(
        request=request,
        name="admin/uploads.html",
        context={
            "app_name": settings.app_name,
            "files": files,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "deleted": request.query_params.get("deleted") == "1",
            "in_use": request.query_params.get("in_use") == "1",
            "error": request.query_params.get("error") == "1",
        },
    )


@router.post("/uploads/delete")
def delete_upload(
    _admin: CurrentAdmin,
    db: DbSession,
    path: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=400, detail="非法图片路径")

    target = (UPLOAD_DIR / relative).resolve()
    root = UPLOAD_DIR.resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")

    url = f"/static/uploads/{relative.as_posix()}"
    if url in all_referenced_upload_urls(db):
        return RedirectResponse("/admin/uploads?in_use=1", status_code=303)

    try:
        target.unlink()
    except OSError:
        return RedirectResponse("/admin/uploads?error=1", status_code=303)

    return RedirectResponse("/admin/uploads?deleted=1", status_code=303)
