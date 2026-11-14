import type { Metadata } from "next";

import { PostEditor } from "@/components/admin/post-editor";
import { getSiteInfo } from "@/lib/api/fetchers";

export const metadata: Metadata = {
  title: "新建文章 · 后台",
  robots: { index: false, follow: false },
};

export default async function NewPostPage() {
  const site = await getSiteInfo();

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>新建文章</h1>
          <p>写一篇新文章。</p>
        </div>
      </header>

      <PostEditor today={site.today} />
    </>
  );
}
