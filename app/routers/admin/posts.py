"""
========== 后台文章管理 ==========
"""

from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select

from app.auth import CurrentAdmin
from app.config import settings
from app.csrf import verify_csrf
from app.deps import DbSession
from app.markdown import headings_for, render_markdown
from app.models import BlogPost
from app.routers.admin.common import (
    PAGE_SIZE,
    fill_post,
    page_slice,
    post_form_values,
    validate_content_fields,
)
from app.services.content import reading_minutes
from app.services.uploads import (
    append_uploaded_image,
    delete_unreferenced_uploads,
    upload_urls_in_text,
)
from app.templating import templates

router = APIRouter()


@router.get("/posts")
def admin_posts(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(BlogPost)) or 0
    page, total_pages = page_slice(page, total)
    posts = db.scalars(
        select(BlogPost)
        .order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/posts.html",
        context={
            "app_name": settings.app_name,
            "posts": posts,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "today": date.today(),
            "saved": request.query_params.get("saved") == "1",
            "deleted": request.query_params.get("deleted") == "1",
        },
    )


@router.get("/posts/{post_id}/edit")
def post_edit_page(request: Request, _admin: CurrentAdmin, post_id: int, db: DbSession):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/post_form.html",
        context={
            "app_name": settings.app_name,
            "post": post,
            "form": post_form_values(post),
        },
    )


@router.get("/posts/{post_id}/preview")
def post_preview(
    request: Request,
    _admin: CurrentAdmin,
    post_id: int,
    db: DbSession,
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/post_preview.html",
        context={
            "app_name": settings.app_name,
            "post": post,
            "content_html": post.content_html or render_markdown(post.content),
            "toc": headings_for(post.content),
            "read_minutes": reading_minutes(post.content),
        },
    )


@router.post("/posts/{post_id}/edit")
def post_edit(
    request: Request,
    _admin: CurrentAdmin,
    post_id: int,
    db: DbSession,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    published_at: str = Form(...),
    tags: str = Form(""),
    slug: str = Form(""),
    is_published: bool = Form(False),
    image: UploadFile | None = File(None),
    image_alt: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    form = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "content": content,
        "published_at": published_at,
        "tags": tags,
        "is_published": is_published,
    }

    error, published_date = validate_content_fields(
        title, summary, content, published_at
    )
    if error is None:
        content, image_error = append_uploaded_image(content, image, image_alt)
        form["content"] = content
        if image_error is not None:
            error = image_error

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/post_form.html",
            context={
                "app_name": settings.app_name,
                "post": post,
                "form": form,
                "error": error,
            },
            status_code=400,
        )

    assert published_date is not None
    old_urls = upload_urls_in_text(post.content, post.content_html)
    fill_post(
        db,
        post,
        title,
        summary,
        content,
        published_date,
        tags,
        is_published,
        slug,
    )
    db.commit()
    delete_unreferenced_uploads(db, old_urls)

    return RedirectResponse("/admin/posts?saved=1", status_code=303)


@router.get("/posts/new")
def post_create_page(request: Request, _admin: CurrentAdmin):
    return templates.TemplateResponse(
        request=request,
        name="admin/post_form.html",
        context={
            "app_name": settings.app_name,
            "post": None,
            "form": {
                "title": "",
                "slug": "",
                "summary": "",
                "content": "",
                "published_at": date.today().isoformat(),
                "tags": "",
                "is_published": True,
            },
        },
    )


@router.post("/posts/new")
def post_create(
    request: Request,
    _admin: CurrentAdmin,
    db: DbSession,
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(...),
    published_at: str = Form(...),
    tags: str = Form(""),
    slug: str = Form(""),
    is_published: bool = Form(False),
    image: UploadFile | None = File(None),
    image_alt: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    form = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "content": content,
        "published_at": published_at,
        "tags": tags,
        "is_published": is_published,
    }

    error, published_date = validate_content_fields(
        title, summary, content, published_at
    )
    if error is None:
        content, image_error = append_uploaded_image(content, image, image_alt)
        form["content"] = content
        if image_error is not None:
            error = image_error

    if error is not None:
        return templates.TemplateResponse(
            request=request,
            name="admin/post_form.html",
            context={
                "app_name": settings.app_name,
                "post": None,
                "form": form,
                "error": error,
            },
            status_code=400,
        )

    assert published_date is not None
    post = BlogPost()
    fill_post(
        db,
        post,
        title,
        summary,
        content,
        published_date,
        tags,
        is_published,
        slug,
    )
    db.add(post)
    db.commit()

    return RedirectResponse("/admin/posts?saved=1", status_code=303)


@router.get("/posts/{post_id}/delete")
def post_delete_confirm(
    request: Request, _admin: CurrentAdmin, post_id: int, db: DbSession
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    return templates.TemplateResponse(
        request=request,
        name="admin/delete_confirm.html",
        context={
            "app_name": settings.app_name,
            "item_title": post.title,
            "item_type": "文章",
            "delete_url": f"/admin/posts/{post.id}/delete",
            "cancel_url": "/admin/posts",
        },
    )


@router.post("/posts/{post_id}/delete")
def post_delete(
    post_id: int,
    _admin: CurrentAdmin,
    db: DbSession,
    _csrf: None = Depends(verify_csrf),
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    candidates = upload_urls_in_text(post.content, post.content_html)
    db.delete(post)
    db.commit()
    delete_unreferenced_uploads(db, candidates)
    return RedirectResponse("/admin/posts?deleted=1", status_code=303)
