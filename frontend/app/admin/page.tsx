import Link from "next/link";

import { getAdminDashboard } from "@/lib/api/admin";

export default async function AdminDashboardPage() {
  const data = await getAdminDashboard();
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  const stats = [
    {
      label: "文章",
      value: data.post_count,
      note: "含草稿与未来文章",
      href: "/admin/posts",
      legacy: false,
    },
    {
      label: "动态",
      value: data.moment_count,
      href: "/admin/moments",
      legacy: true,
    },
    {
      label: "留言",
      value: data.message_count,
      href: "/admin/messages",
      legacy: true,
    },
    {
      label: "评论",
      value: data.comment_count,
      note: `待审核 ${data.pending_count}`,
      href: "/admin/comments",
      legacy: true,
    },
    {
      label: "动态评论",
      value: data.moment_comment_count,
      note: `待审核 ${data.moment_pending_count}`,
      href: "/admin/moment-comments",
      legacy: true,
    },
    {
      label: "用户",
      value: data.user_count,
      href: "/admin/users",
      legacy: true,
    },
  ];

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>仪表盘</h1>
          <p>博客当前的数据概览。</p>
        </div>
        <a href="/admin/posts/new" className="btn btn-primary">
          新建文章
        </a>
      </header>

      <div className="admin-stat-grid">
        {stats.map((stat) =>
          stat.legacy ? (
            <a
              key={stat.label}
              href={stat.href}
              className="glass glass-hover admin-stat"
            >
              <div className="admin-stat-label">{stat.label}</div>
              <div className="admin-stat-value">{stat.value}</div>
              {stat.note ? (
                <div className="admin-stat-note">{stat.note}</div>
              ) : null}
            </a>
          ) : (
            <Link
              key={stat.label}
              href={stat.href}
              className="glass glass-hover admin-stat"
            >
              <div className="admin-stat-label">{stat.label}</div>
              <div className="admin-stat-value">{stat.value}</div>
              {stat.note ? (
                <div className="admin-stat-note">{stat.note}</div>
              ) : null}
            </Link>
          ),
        )}
      </div>

      <section className="glass admin-panel">
        <h2>Phase 3 进度</h2>
        <p>
          仪表盘和文章列表已迁移到 Next.js。文章编辑、评论/动态审核、用户与安全设置
          暂时继续使用旧后台；后续切片会逐页迁移。
        </p>
      </section>
    </>
  );
}
