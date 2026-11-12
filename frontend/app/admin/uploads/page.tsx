import type { Metadata } from "next";

import { AdminActionButton } from "@/components/admin/admin-action-button";
import { Pagination } from "@/components/ui/pagination";
import { getAdminUploads } from "@/lib/api/admin";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = {
  title: "图片 · 后台",
  robots: { index: false, follow: false },
};

function formatSize(size: number): string {
  return `${(size / 1024).toFixed(1)} KB`;
}

export default async function AdminUploadsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getAdminUploads(page);
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>图片管理</h1>
          <p>共 {data.meta.total} 个文件</p>
        </div>
      </header>

      {data.items.length === 0 ? (
        <div className="glass admin-empty">还没有上传图片。</div>
      ) : (
        <div className="admin-table">
          {data.items.map((file) => (
            <article key={file.name} className="glass admin-row">
              <div className="admin-row-main">
                <div className="admin-row-title">
                  <a href={file.url} target="_blank" rel="noopener">
                    {file.name}
                  </a>
                  <span
                    className={`admin-status ${
                      file.referenced ? "is-published" : "is-draft"
                    }`}
                  >
                    {file.referenced ? "已引用" : "未引用"}
                  </span>
                </div>
                <div className="admin-row-meta">
                  <span>{formatSize(file.size)}</span>
                </div>
              </div>

              <div className="admin-row-actions">
                {file.referenced ? (
                  <span className="admin-row-meta">使用中</span>
                ) : (
                  <AdminActionButton
                    endpoint="/api/v1/admin/uploads/delete"
                    body={{ path: file.name }}
                    label="删除"
                    confirmMessage="确定删除这张图片吗？"
                  />
                )}
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
          target <= 1 ? "/admin/uploads" : `/admin/uploads?page=${target}`
        }
      />
    </>
  );
}
