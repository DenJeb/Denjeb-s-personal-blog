import type { Metadata } from "next";
import Link from "next/link";

import { AdminDeleteButton } from "@/components/admin/admin-delete-button";
import { Pagination } from "@/components/ui/pagination";
import { getAdminMoments } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/date";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "动态 · 后台",
  robots: { index: false, follow: false },
};

function momentHref(momentId: number, page: number): string {
  const query = page > 1 ? `?page=${page}` : "";
  return `/moments${query}#moment-${momentId}`;
}

function excerpt(content: string): string {
  return content.length > 80 ? `${content.slice(0, 80)}…` : content;
}

export default async function AdminMomentsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminMoments(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>动态管理</h1>
          <p>共 {data.meta.total} 条</p>
        </div>
        <Link href="/admin/moments/new" className="btn btn-primary">
          发布动态
        </Link>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">还没有动态。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((moment) => (
            <article key={moment.id} className="glass admin-row">
              <div className="admin-row-main">
                <p
                  className="admin-row-content"
                  title={moment.content}
                >
                  {excerpt(moment.content)}
                </p>
                <div className="admin-row-meta">
                  <time dateTime={moment.created_at}>
                    {formatDateTime(moment.created_at)}
                  </time>
                </div>
              </div>

              <div className="admin-row-actions">
                <a
                  href={momentHref(moment.id, moment.public_page)}
                  className="btn btn-ghost"
                  target="_blank"
                  rel="noopener"
                >
                  预览
                </a>
                <Link
                  href={
                    data.meta.page > 1
                      ? `/admin/moments/${moment.id}/edit?page=${data.meta.page}`
                      : `/admin/moments/${moment.id}/edit`
                  }
                  className="btn btn-ghost"
                >
                  编辑
                </Link>
                <AdminDeleteButton
                  endpoint={`/api/v1/admin/moments/${moment.id}`}
                  confirmMessage="确定删除这条动态吗？"
                />
              </div>
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
          target <= 1 ? "/admin/moments" : `/admin/moments?page=${target}`
        }
      />
    </>
  );
}
