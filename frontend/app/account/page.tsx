import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/layout/logout-button";
import { getCurrentUser } from "@/lib/api/fetchers";

export const metadata: Metadata = {
  title: "我的账号",
  robots: { index: false, follow: false },
};

export default async function AccountPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/account");
  }

  return (
    <section className="shell auth-shell">
      <div className="glass auth-card">
        <h1 className="auth-title">我的账号</h1>
        <p className="auth-subtitle">
          当前登录：<strong>{user.name}</strong>
        </p>
        <p className="auth-subtitle">评论和留言会显示这个昵称。</p>

        <div className="auth-form">
          <LogoutButton />
        </div>

        <div className="auth-links account-links">
          <Link href="/">返回首页</Link>
          <Link href="/guestbook">去留言板</Link>
          <a href="/account/delete">注销账号</a>
        </div>
      </div>
    </section>
  );
}
