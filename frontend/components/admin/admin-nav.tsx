"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/admin", label: "仪表盘", legacy: false },
  { href: "/admin/posts", label: "文章", legacy: false },
  { href: "/admin/comments", label: "评论", legacy: true },
  { href: "/admin/moments", label: "动态", legacy: true },
  { href: "/admin/moment-comments", label: "动态评论", legacy: true },
  { href: "/admin/messages", label: "留言", legacy: true },
  { href: "/admin/users", label: "用户", legacy: true },
  { href: "/admin/uploads", label: "图片", legacy: true },
  { href: "/admin/security", label: "安全", legacy: true },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/admin") {
    return pathname === "/admin" || pathname === "/admin/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="后台导航" className="admin-nav">
      {navItems.map((item) => {
        if (item.legacy) {
          // Legacy Jinja pages need a full document navigation.
          return (
            <a key={item.href} href={item.href}>
              {item.label}
            </a>
          );
        }

        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={active ? "is-active" : undefined}
            aria-current={active ? "page" : undefined}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
