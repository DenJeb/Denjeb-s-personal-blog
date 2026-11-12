import type { Metadata } from "next";

import { AdminActionButton } from "@/components/admin/admin-action-button";
import { AdminDeleteButton } from "@/components/admin/admin-delete-button";
import { Pagination } from "@/components/ui/pagination";
import { getAdminUsers } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/date";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "用户 · 后台",
  robots: { index: false, follow: false },
};

export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminUsers(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>用户管理</h1>
          <p>共 {data.meta.total} 个注册用户</p>
        </div>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">还没有注册用户。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((user) => (
            <article key={user.id} className="glass admin-row">
              <div className="admin-row-main">
                <div className="admin-row-title">
                  <span>{user.email ?? "-"}</span>
                  <span
                    className={`admin-status ${
                      user.is_active ? "is-published" : "is-draft"
                    }`}
                  >
                    {user.is_active ? "正常" : "已禁用"}
                  </span>
                </div>
                <div className="admin-row-meta">
                  <span>{user.username}</span>
                  <time dateTime={user.created_at}>
                    {formatDateTime(user.created_at)}
                  </time>
                </div>
              </div>

              <div className="admin-row-actions">
                <AdminActionButton
                  endpoint={`/api/v1/admin/users/${user.id}/toggle`}
                  label={user.is_active ? "禁用" : "启用"}
                />
                <AdminDeleteButton
                  endpoint={`/api/v1/admin/users/${user.id}`}
                  confirmMessage="确定删除这个用户吗？"
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
          target <= 1 ? "/admin/users" : `/admin/users?page=${target}`
        }
      />
    </>
  );
}
