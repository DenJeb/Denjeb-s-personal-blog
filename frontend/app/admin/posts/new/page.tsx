import type { Metadata } from "next";

import { PostEditor } from "@/components/admin/post-editor";

export const metadata: Metadata = {
  title: "新建文章 · 后台",
  robots: { index: false, follow: false },
};

function siteToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
  }).format(new Date());
}

export default function NewPostPage() {
  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>新建文章</h1>
          <p>写一篇新文章。</p>
        </div>
      </header>

      <PostEditor today={siteToday()} />
    </>
  );
}
