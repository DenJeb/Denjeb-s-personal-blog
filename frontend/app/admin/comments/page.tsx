import type { Metadata } from "next";

import { ModerationActions } from "@/components/admin/moderation-actions";
import { Pagination } from "@/components/ui/pagination";
import { getAdminComments } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/date";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "评论 · 后台",
  robots: { index: false, follow: false },
};

export default async function AdminCommentsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminComments(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>评论管理</h1>
          <p>共 {data.meta.total} 条</p>
        </div>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">还没有评论。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((comment) => (
            <article key={comment.id} className="glass admin-row">
              <div className="admin-row-main">
                <div className="admin-row-title">
                  <a
                    href={`/posts/${comment.post_slug ?? comment.post_id}`}
                    target="_blank"
                    rel="noopener"
                  >
                    {comment.post_title}
                  </a>
                  <span
                    className={`admin-status ${
                      comment.is_approved ? "is-published" : "is-draft"
                    }`}
                  >
                    {comment.is_approved ? "已通过" : "待审核"}
                  </span>
                </div>
                <div className="admin-row-meta">
                  <span>{comment.author_name}</span>
                  <time dateTime={comment.created_at}>
                    {formatDateTime(comment.created_at)}
                  </time>
                </div>
                <p className="admin-row-content">{comment.content}</p>
              </div>

              <ModerationActions
                approveEndpoint={`/api/v1/admin/comments/${comment.id}/approve`}
                deleteEndpoint={`/api/v1/admin/comments/${comment.id}`}
                approved={comment.is_approved}
              />
            </article>
          ))}
        </div>
      )}

      <Pagination
        page={data.meta.page}
        totalPages={data.meta.total_pages}
        hasPrev={data.meta.has_prev}
        hasNext={data.meta.has_next}
        buildHref={(target) =>
          target <= 1 ? "/admin/comments" : `/admin/comments?page=${target}`
        }
      />
    </>
  );
}
