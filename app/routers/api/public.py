"""
========== 公开 JSON API ==========

只读接口，供未来的 Next.js 前台消费。现有 Jinja/HTMX 页面继续使用
app.routers.public，二者共享 service 层。
"""

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.constants import (
    COMMENTS_PER_PAGE,
    MESSAGES_PER_PAGE,
    MOMENTS_PER_PAGE,
    POSTS_PER_PAGE,
)
from app.deps import DbSession
from app.markdown import headings_for, render_markdown
from app.models import BlogPost
from app.schemas.public import (
    ArchiveMonth,
    ArchiveResponse,
    ArchiveYear,
    CommentItem,
    CommentListResponse,
    MessageItem,
    MessageListResponse,
    MomentCommentItem,
    MomentItem,
    MomentListResponse,
    PageMeta,
    PostDetail,
    PostLink,
    PostListResponse,
    PostSummary,
    SiteInfo,
    TagItem,
    TagListResponse,
    TocItem,
)
from app.services.content import (
    adjacent_posts,
    all_visible_posts,
    archive_tree,
    attach_sorted_tags,
    find_post,
    is_post_public,
    moment_comments_for,
    paginate_comments,
    paginate_messages,
    paginate_moments,
    paginate_posts,
    reading_minutes,
    related_posts,
    tag_initial_sort_key,
    tag_sort_key,
    visible_tag_counts,
)

router = APIRouter()

PER_PAGE_MAX = 50


def _site_url() -> str:
    return settings.site_url.rstrip("/")


def _post_slug(post: BlogPost) -> str:
    return post.slug or str(post.id)


def _post_url(post: BlogPost) -> str:
    return f"{_site_url()}/posts/{_post_slug(post)}"


def _post_tags(post: BlogPost) -> list[str]:
    tags = getattr(post, "sorted_tags", None) or sorted(
        post.tags or [], key=tag_initial_sort_key
    )
    return list(tags)


def _post_summary(post: BlogPost) -> PostSummary:
    return PostSummary(
        id=post.id,
        title=post.title,
        slug=_post_slug(post),
        url=_post_url(post),
        summary=post.summary,
        published_at=post.published_at,
        tags=_post_tags(post),
        reading_minutes=reading_minutes(post.content),
    )


def _post_link(post: BlogPost) -> PostLink:
    return PostLink(
        title=post.title,
        slug=_post_slug(post),
        url=_post_url(post),
        published_at=post.published_at,
    )


def _meta(page: int, per_page: int, total: int, total_pages: int) -> PageMeta:
    return PageMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


@router.get("/site", response_model=SiteInfo)
def site_info():
    return SiteInfo(
        app_name=settings.app_name,
        author=settings.author_name,
        site_url=_site_url(),
    )


@router.get("/posts", response_model=PostListResponse)
def list_posts(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(POSTS_PER_PAGE, ge=1, le=PER_PAGE_MAX),
    tag: str | None = Query(None, max_length=100),
    q: str | None = Query(None, max_length=100),
):
    query = q.strip() if q else None
    posts, total, page, total_pages = paginate_posts(
        db,
        page,
        per_page,
        tag=tag,
        query=query,
    )
    return PostListResponse(
        items=[_post_summary(post) for post in posts],
        meta=_meta(page, per_page, total, total_pages),
    )


@router.get("/posts/{identifier}", response_model=PostDetail, name="api_post_detail")
def post_detail(identifier: str, db: DbSession):
    post = find_post(db, identifier)
    if post is None or not is_post_public(post):
        raise HTTPException(status_code=404, detail="文章不存在！")

    attach_sorted_tags([post])
    previous_post, next_post = adjacent_posts(db, post)
    content_html = post.content_html or render_markdown(post.content)
    toc = [TocItem(**item) for item in headings_for(post.content)]

    return PostDetail(
        **_post_summary(post).model_dump(),
        content=post.content,
        content_html=content_html,
        updated_at=post.updated_at,
        toc=toc,
        previous_post=_post_link(previous_post) if previous_post else None,
        next_post=_post_link(next_post) if next_post else None,
        related_posts=[_post_summary(item) for item in related_posts(db, post)],
    )


@router.get("/posts/{identifier}/comments", response_model=CommentListResponse)
def post_comments(
    identifier: str,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(COMMENTS_PER_PAGE, ge=1, le=PER_PAGE_MAX),
):
    post = find_post(db, identifier)
    if post is None or not is_post_public(post):
        raise HTTPException(status_code=404, detail="文章不存在！")

    comments, total, page, total_pages = paginate_comments(db, post, page, per_page)
    return CommentListResponse(
        items=[
            CommentItem(
                id=comment.id,
                author_name=comment.author_name,
                content=comment.content,
                created_at=comment.created_at,
            )
            for comment in comments
        ],
        meta=_meta(page, per_page, total, total_pages),
    )


@router.get("/tags", response_model=TagListResponse)
def list_tags(db: DbSession):
    counts = visible_tag_counts(db)
    items = [
        TagItem(name=tag, count=count)
        for tag, count in sorted(counts.items(), key=tag_sort_key)
    ]
    return TagListResponse(items=items)


@router.get("/archive", response_model=ArchiveResponse)
def archive(db: DbSession):
    tree = archive_tree(db)
    years = []
    total = 0
    for year in sorted(tree, reverse=True):
        months = []
        for month in sorted(tree[year], reverse=True):
            posts = tree[year][month]
            total += len(posts)
            months.append(
                ArchiveMonth(
                    month=month,
                    posts=[_post_summary(post) for post in posts],
                )
            )
        years.append(ArchiveYear(year=year, months=months))
    return ArchiveResponse(total=total, years=years)


@router.get("/search", response_model=PostListResponse)
def search(
    db: DbSession,
    q: str = Query(..., max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(POSTS_PER_PAGE, ge=1, le=PER_PAGE_MAX),
):
    query = q.strip()
    if not query:
        return PostListResponse(
            items=[],
            meta=_meta(1, per_page, 0, 1),
        )

    posts, total, page, total_pages = paginate_posts(db, page, per_page, query=query)
    return PostListResponse(
        items=[_post_summary(post) for post in posts],
        meta=_meta(page, per_page, total, total_pages),
    )


@router.get("/moments", response_model=MomentListResponse)
def list_moments(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(MOMENTS_PER_PAGE, ge=1, le=PER_PAGE_MAX),
):
    moments, total, page, total_pages = paginate_moments(db, page, per_page)
    comments_by_moment, comment_counts = moment_comments_for(
        db, [moment.id for moment in moments]
    )

    items = [
        MomentItem(
            id=moment.id,
            content=moment.content,
            created_at=moment.created_at,
            comment_count=comment_counts.get(moment.id, 0),
            comments=[
                MomentCommentItem(
                    id=comment.id,
                    author_name=comment.author_name,
                    content=comment.content,
                    created_at=comment.created_at,
                )
                for comment in comments_by_moment.get(moment.id, [])
            ],
        )
        for moment in moments
    ]
    return MomentListResponse(
        items=items,
        meta=_meta(page, per_page, total, total_pages),
    )


@router.get("/guestbook", response_model=MessageListResponse)
def list_guestbook(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(MESSAGES_PER_PAGE, ge=1, le=PER_PAGE_MAX),
):
    messages, total, page, total_pages = paginate_messages(db, page, per_page)
    return MessageListResponse(
        items=[
            MessageItem(
                id=message.id,
                author_name=message.author_name,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
        meta=_meta(page, per_page, total, total_pages),
    )


@router.get("/recent", response_model=list[PostSummary])
def recent_posts(
    db: DbSession,
    limit: int = Query(5, ge=1, le=20),
):
    return [_post_summary(post) for post in all_visible_posts(db, limit=limit)]
