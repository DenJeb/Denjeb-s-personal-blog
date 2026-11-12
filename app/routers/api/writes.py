"""
========== 评论 / 动态评论 / 留言写入 API ==========
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.auth import current_commenter
from app.csrf import verify_csrf_header
from app.deps import DbSession
from app.models import Moment
from app.schemas.writes import (
    ContentRequest,
    PostCommentRequest,
    WriteResponse,
)
from app.services.content import find_post, is_post_public
from app.services.interactions import (
    INTERACTION_COOLDOWN_SECONDS,
    InteractionResult,
    create_comment,
    create_message,
    create_moment_comment,
)

router = APIRouter()


def _require_commenter(request: Request, db: Session) -> tuple[str, str, int | None]:
    author, actor_key, user_id = current_commenter(request, db)
    if author is None or actor_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return author, actor_key, user_id


def _raise_for_result(result: InteractionResult) -> None:
    if result.ok:
        return
    if result.code == "too_fast":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=result.message,
            headers={"Retry-After": str(INTERACTION_COOLDOWN_SECONDS)},
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=result.message,
    )


@router.post(
    "/posts/{identifier}/comments",
    response_model=WriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_comment(
    identifier: str,
    payload: PostCommentRequest,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    post = find_post(db, identifier)
    if post is None or not is_post_public(post):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在！",
        )

    author, actor_key, user_id = _require_commenter(request, db)
    if payload.website.strip():
        return WriteResponse(ok=True, message="评论已提交，审核通过后会显示。")

    result = create_comment(db, post, author, actor_key, user_id, payload.content)
    _raise_for_result(result)
    return WriteResponse(ok=True, message=result.message)


@router.post(
    "/moments/{moment_id}/comments",
    response_model=WriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def moment_comment(
    moment_id: int,
    payload: ContentRequest,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    moment = db.get(Moment, moment_id)
    if moment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在！",
        )

    author, actor_key, user_id = _require_commenter(request, db)
    if payload.website.strip():
        return WriteResponse(ok=True, message="评论已提交，审核通过后会显示。")

    result = create_moment_comment(
        db, moment, author, actor_key, user_id, payload.content
    )
    _raise_for_result(result)
    return WriteResponse(ok=True, message=result.message)


@router.post(
    "/guestbook",
    response_model=WriteResponse,
    status_code=status.HTTP_201_CREATED,
)
def guestbook(
    payload: ContentRequest,
    request: Request,
    db: DbSession,
    _csrf: None = Depends(verify_csrf_header),
):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )

    if payload.website.strip():
        return WriteResponse(ok=True, message="留言已提交。")

    result = create_message(db, user, payload.content)
    _raise_for_result(result)
    return WriteResponse(ok=True, message=result.message)
