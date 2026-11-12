"""
========== 后台内容 JSON API：文章、上传、动态、留言 ==========
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentAdminApi
from app.csrf import verify_csrf_header
from app.deps import DbSession
from app.models import BlogPost, Message, Moment
from app.routers.api.admin_common import page_meta, post_summary
from app.schemas.admin import (
    AdminInlineUpload,
    AdminMessageItem,
    AdminMessageList,
    AdminMomentItem,
    AdminMomentList,
    AdminMomentWriteRequest,
    AdminOkResponse,
    AdminPostDetail,
    AdminPostWriteRequest,
    AdminPreviewRequest,
    AdminPreviewResponse,
    AdminUploadDeleteRequest,
    AdminUploadItem,
    AdminUploadList,
)
from app.services.content import moment_page
from app.services.interactions import (
    create_moment,
    delete_message,
    delete_moment,
    update_moment,
    validate_moment_content,
)
from app.services.pagination import ADMIN_PAGE_SIZE, page_slice
from app.services.posts import (
    create_post,
    delete_post,
    parse_tags,
    preview_html,
    update_post,
    validate_post_fields,
)
from app.services.uploads import (
    UPLOAD_DIR,
    all_referenced_upload_urls,
    delete_upload_by_path,
    save_uploaded_image,
)

router = APIRouter(prefix="/admin")


def _post_detail(post: BlogPost) -> AdminPostDetail:
    return AdminPostDetail(
        **post_summary(post).model_dump(),
        content=post.content,
        content_html=post.content_html,
    )


def _moment_item(db: Session, moment: Moment) -> AdminMomentItem:
    return AdminMomentItem(
        id=moment.id,
        content=moment.content,
        created_at=moment.created_at,
        public_page=moment_page(db, moment),
    )


@router.post(
    "/posts",
    response_model=AdminPostDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_post_endpoint(
    payload: AdminPostWriteRequest,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    error, published_date = validate_post_fields(
        payload.title, payload.summary, payload.content, payload.published_at
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)

    assert published_date is not None
    post = create_post(
        db,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        published_at=published_date,
        tags=parse_tags(payload.tags),
        is_published=payload.is_published,
        slug=payload.slug,
    )
    return _post_detail(post)


@router.put("/posts/{post_id}", response_model=AdminPostDetail)
def update_post_endpoint(
    post_id: int,
    payload: AdminPostWriteRequest,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    error, published_date = validate_post_fields(
        payload.title, payload.summary, payload.content, payload.published_at
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)

    assert published_date is not None
    update_post(
        db,
        post,
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        published_at=published_date,
        tags=parse_tags(payload.tags),
        is_published=payload.is_published,
        slug=payload.slug,
    )
    return _post_detail(post)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post_endpoint(
    post_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在！")

    delete_post(db, post)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/posts/preview", response_model=AdminPreviewResponse)
def preview_post_endpoint(
    payload: AdminPreviewRequest,
    _admin: CurrentAdminApi,
    _csrf: None = Depends(verify_csrf_header),
):
    return AdminPreviewResponse(html=preview_html(payload.content))


@router.post("/uploads/inline", response_model=AdminInlineUpload)
def inline_upload_endpoint(
    _admin: CurrentAdminApi,
    image: UploadFile = File(...),
    image_alt: str = Form(""),
    _csrf: None = Depends(verify_csrf_header),
):
    try:
        url = save_uploaded_image(image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    alt = image_alt.strip().replace("[", "").replace("]", "") or "图片"
    return AdminInlineUpload(
        url=url,
        markdown=f"![{alt}]({url})",
    )


@router.get("/uploads", response_model=AdminUploadList)
def list_uploads(
    _admin: CurrentAdminApi,
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
                AdminUploadItem(
                    name=relative,
                    url=url,
                    size=path.stat().st_size,
                    referenced=url in referenced,
                )
            )

    total = len(files)
    page, total_pages = page_slice(page, total)
    start = (page - 1) * ADMIN_PAGE_SIZE
    return AdminUploadList(
        items=files[start : start + ADMIN_PAGE_SIZE],
        meta=page_meta(page, total, total_pages),
    )


@router.post("/uploads/delete", response_model=AdminOkResponse)
def delete_upload_endpoint(
    payload: AdminUploadDeleteRequest,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    result = delete_upload_by_path(db, payload.path)
    if result == "invalid":
        raise HTTPException(status_code=400, detail="非法图片路径")
    if result == "missing":
        raise HTTPException(status_code=404, detail="图片不存在")
    if result == "in_use":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="图片仍被文章引用，不能删除。",
        )
    if result == "error":
        raise HTTPException(status_code=500, detail="删除失败，请稍后重试。")

    return AdminOkResponse(message="图片已删除。")


@router.get("/moments", response_model=AdminMomentList)
def list_moments(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Moment)) or 0
    page, total_pages = page_slice(page, total)
    moments = db.scalars(
        select(Moment)
        .order_by(Moment.created_at.desc(), Moment.id.desc())
        .offset((page - 1) * ADMIN_PAGE_SIZE)
        .limit(ADMIN_PAGE_SIZE)
    ).all()
    return AdminMomentList(
        items=[_moment_item(db, moment) for moment in moments],
        meta=page_meta(page, total, total_pages),
    )


@router.get("/moments/{moment_id}", response_model=AdminMomentItem)
def get_moment_endpoint(
    moment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")
    return _moment_item(db, moment)


@router.post(
    "/moments",
    response_model=AdminMomentItem,
    status_code=status.HTTP_201_CREATED,
)
def create_moment_endpoint(
    payload: AdminMomentWriteRequest,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    error = validate_moment_content(payload.content)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)

    moment = create_moment(db, payload.content)
    return _moment_item(db, moment)


@router.put("/moments/{moment_id}", response_model=AdminMomentItem)
def update_moment_endpoint(
    moment_id: int,
    payload: AdminMomentWriteRequest,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    error = validate_moment_content(payload.content)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)

    update_moment(db, moment, payload.content)
    return _moment_item(db, moment)


@router.delete(
    "/moments/{moment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_moment_endpoint(
    moment_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(status_code=404, detail="动态不存在！")

    delete_moment(db, moment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/messages", response_model=AdminMessageList)
def list_messages(
    _admin: CurrentAdminApi,
    db: DbSession,
    page: int = Query(1, ge=1),
):
    total = db.scalar(select(func.count()).select_from(Message)) or 0
    page, total_pages = page_slice(page, total)
    messages = db.scalars(
        select(Message)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * ADMIN_PAGE_SIZE)
        .limit(ADMIN_PAGE_SIZE)
    ).all()
    return AdminMessageList(
        items=[
            AdminMessageItem(
                id=message.id,
                author_name=message.author_name,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
        meta=page_meta(page, total, total_pages),
    )


@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_message_endpoint(
    message_id: int,
    _admin: CurrentAdminApi,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="留言不存在！")

    delete_message(db, message)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
