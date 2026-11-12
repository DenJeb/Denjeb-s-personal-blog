import type { Metadata } from "next";

import { MomentForm } from "@/components/admin/moment-form";

export const metadata: Metadata = {
  title: "发布动态 · 后台",
  robots: { index: false, follow: false },
};

export default function NewMomentPage() {
  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>发布动态</h1>
          <p>写一条新的动态。</p>
        </div>
      </header>

      <MomentForm initialContent="" />
    </>
  );
}
