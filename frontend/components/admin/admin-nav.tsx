"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/admin", label: "仪表盘" },
  { href: "/admin/posts", label: "文章" },
  { href: "/admin/comments", label: "评论" },
  { href: "/admin/moments", label: "动态" },
  { href: "/admin/moment-comments", label: "动态评论" },
  { href: "/admin/messages", label: "留言" },
  { href: "/admin/users", label: "用户" },
  { href: "/admin/uploads", label: "图片" },
  { href: "/admin/security", label: "安全" },
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
