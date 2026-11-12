import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PostEditor } from "@/components/admin/post-editor";
import { getAdminPost } from "@/lib/api/admin";

export const metadata: Metadata = {
  title: "编辑文章 · 后台",
  robots: { index: false, follow: false },
};

export default async function EditPostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const postId = Number(id);
  if (!Number.isInteger(postId) || postId <= 0) {
    notFound();
  }

  const post = await getAdminPost(postId);
  if (!post) {
    notFound();
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>编辑文章</h1>
          <p>{post.title}</p>
        </div>
      </header>

      <PostEditor
        initial={{
          id: post.id,
          title: post.title,
          slug: post.slug,
          summary: post.summary,
          content: post.content,
          published_at: post.published_at,
          tags: post.tags,
          is_published: post.is_published,
        }}
        today={post.published_at}
      />
    </>
  );
}
