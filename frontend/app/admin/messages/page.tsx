import type { Metadata } from "next";

import { AdminDeleteButton } from "@/components/admin/admin-delete-button";
import { Pagination } from "@/components/ui/pagination";
import { getAdminMessages } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/date";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "留言 · 后台",
  robots: { index: false, follow: false },
};

function excerpt(content: string): string {
  return content.length > 80 ? `${content.slice(0, 80)}…` : content;
}

export default async function AdminMessagesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminMessages(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>留言管理</h1>
          <p>共 {data.meta.total} 条</p>
        </div>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">还没有留言。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((message) => (
            <article key={message.id} className="glass admin-row">
              <div className="admin-row-main">
                <div className="admin-row-title">
                  <span>{message.author_name}</span>
                </div>
                <div className="admin-row-meta">
                  <time dateTime={message.created_at}>
                    {formatDateTime(message.created_at)}
                  </time>
                </div>
                <p
                  className="admin-row-content"
                  title={message.content}
                >
                  {excerpt(message.content)}
                </p>
              </div>

              <div className="admin-row-actions">
                <AdminDeleteButton
                  endpoint={`/api/v1/admin/messages/${message.id}`}
                  confirmMessage="确定删除这条留言吗？"
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
          target <= 1 ? "/admin/messages" : `/admin/messages?page=${target}`
        }
      />
    </>
  );
}
