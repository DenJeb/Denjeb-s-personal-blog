import type { Metadata } from "next";

import { Pagination } from "@/components/ui/pagination";
import { getAdminPosts } from "@/lib/api/admin";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "文章 · 后台",
  robots: { index: false, follow: false },
};

export default async function AdminPostsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminPosts(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>文章</h1>
          <p>共 {data.meta.total} 篇，包含草稿和未来文章。</p>
        </div>
        <a href="/admin/posts/new" className="btn btn-primary">
          新建文章
        </a>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">暂无文章。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((post) => {
            const status = !post.is_published
              ? { label: "草稿", className: "is-draft" }
              : post.is_public
                ? { label: "已发布", className: "is-published" }
                : { label: "未到日期", className: "is-scheduled" };

            return (
              <article key={post.id} className="glass admin-row">
                <div className="admin-row-main">
                  <div className="admin-row-title">
                    <a href={`/admin/posts/${post.id}/edit`}>{post.title}</a>
                    <span className={`admin-status ${status.className}`}>
                      {status.label}
                    </span>
                  </div>
                  <div className="admin-row-meta">
                    <time dateTime={post.published_at}>{post.published_at}</time>
                    <span>{post.reading_minutes} 分钟</span>
                    {post.tags.map((tag) => (
                      <span key={tag}>#{tag}</span>
                    ))}
                  </div>
                </div>

                <div className="admin-row-actions">
                  <a
                    href={`/admin/posts/${post.id}/edit`}
                    className="btn btn-ghost"
                  >
                    编辑
                  </a>
                  <a
                    href={`/admin/posts/${post.id}/preview`}
                    className="btn btn-ghost"
                    target="_blank"
                    rel="noopener"
                  >
                    预览
                  </a>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <Pagination
        page={data.meta.page}
        totalPages={data.meta.total_pages}
        hasPrev={data.meta.has_prev}
        hasNext={data.meta.has_next}
        buildHref={(target) =>
          target <= 1 ? "/admin/posts" : `/admin/posts?page=${target}`
        }
      />
    </>
  );
}
