import type { Metadata } from "next";

import { SecurityPanel } from "@/components/admin/security-panel";
import { getAdminSecurity } from "@/lib/api/admin";

export const metadata: Metadata = {
  title: "安全 · 后台",
  robots: { index: false, follow: false },
};

export default async function AdminSecurityPage() {
  const data = await getAdminSecurity();
  if (!data) {
    // The parent layout renders the login prompt for anonymous visitors.
    return null;
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>安全设置</h1>
          <p>为后台登录增加一层保护。</p>
        </div>
      </header>

      <SecurityPanel initial={data} />
    </>
  );
}
