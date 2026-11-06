import Link from "next/link";

import { getCurrentUser, getSiteInfo } from "@/lib/api/fetchers";
import { loadSiteInfo } from "@/lib/api/load-site-info";

import { ThemeToggle } from "./theme-toggle";

const navItems = [
  { href: "/posts", label: "文章" },
  { href: "/tags", label: "标签" },
  { href: "/archive", label: "归档" },
  { href: "/search", label: "搜索" },
  { href: "/moments", label: "动态" },
  { href: "/guestbook", label: "留言" },
  { href: "/about", label: "关于" },
];

export async function SiteHeader() {
  const [site, user] = await Promise.all([
    loadSiteInfo(getSiteInfo),
    getCurrentUser(),
  ]);

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Link href="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>{site.app_name}</span>
        </Link>

        <nav aria-label="主导航" className="site-nav">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className="nav-link">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          <ThemeToggle />
          {user ? (
            <Link href="/account" className="btn btn-ghost">
              {user.name}
            </Link>
          ) : (
            <Link href="/login" className="btn btn-ghost">
              登录
            </Link>
          )}
        </div>

        <details className="mobile-nav">
          <summary className="btn btn-ghost">菜单</summary>
          <nav aria-label="移动导航" className="mobile-nav-panel glass">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
        </details>
      </div>
    </header>
  );
}
