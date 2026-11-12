import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { AdminLogoutButton } from "@/components/admin/admin-logout-button";
import { AdminNav } from "@/components/admin/admin-nav";
import { getAdminMe } from "@/lib/api/admin";

export const metadata: Metadata = {
  title: "后台",
  robots: { index: false, follow: false },
};

export default async function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  const admin = await getAdminMe();

  if (!admin) {
    return (
      <div className="admin-shell admin-shell-login">
        <div className="glass admin-login">
          <h1>需要管理员登录</h1>
          <p>后台使用邮箱验证码 + 密码登录；登录后回到这里。</p>
          <div>
            <a href="/admin/login" className="btn btn-primary">
              去登录
            </a>
            <Link href="/" className="btn btn-ghost">
              返回前台
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <Link href="/admin" className="admin-brand">
          <span className="brand-mark" aria-hidden="true" />
          后台
        </Link>

        <AdminNav />

        <div className="admin-side-footer">
          <div className="admin-user">{admin.username}</div>
          <Link href="/" className="admin-back">
            返回前台
          </Link>
          <AdminLogoutButton />
        </div>
      </aside>

      <div className="admin-main">
        <header className="admin-topbar">
          <span>管理后台</span>
          <Link href="/" className="admin-top-link">
            查看前台
          </Link>
        </header>
        <div className="admin-content">{children}</div>
      </div>
    </div>
  );
}
