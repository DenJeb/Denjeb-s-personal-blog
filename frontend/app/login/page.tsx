import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { getCurrentUser } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { safeNext } from "@/lib/safe-next";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = pageMetadata({
  title: "登录",
  description: "登录后参与评论和留言",
  path: "/login",
});

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  if (await getCurrentUser()) {
    redirect("/");
  }

  const { next } = await searchParams;

  return (
    <section className="shell auth-shell">
      <div className="glass auth-card">
        <h1 className="auth-title">登录</h1>
        <p className="auth-subtitle">登录后可以评论、留言，也可以管理自己的账号。</p>
        <LoginForm next={safeNext(firstParam(next))} />
      </div>
    </section>
  );
}
