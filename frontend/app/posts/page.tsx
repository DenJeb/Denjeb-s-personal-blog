import type { Metadata } from "next";
import Link from "next/link";

import { PostCard } from "@/components/post/post-card";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getPosts } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = pageMetadata({
  title: "文章",
  description: "全部文章",
  path: "/posts",
});

export default async function PostsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string | string[] }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(firstParam(rawPage));
  const data = await getPosts({ page });

  return (
    <section className="shell">
      <PageHeader
        title="文章"
        description={`共 ${data.meta.total} 篇文章，按发布时间倒序。`}
      />

      {data.items.length === 0 ? (
        <div className="glass empty-state">
          <p>没有更多文章</p>
          <Link href="/posts">回到第一页</Link>
        </div>
      ) : (
        <div className="post-grid">
          {data.items.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}

      <Pagination
        page={data.meta.page}
        totalPages={data.meta.total_pages}
        hasPrev={data.meta.has_prev}
        hasNext={data.meta.has_next}
        buildHref={(target) =>
          target <= 1 ? "/posts" : `/posts?page=${target}`
        }
      />
    </section>
  );
}
