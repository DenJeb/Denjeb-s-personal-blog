import type { Metadata } from "next";
import Link from "next/link";

import { PostCard } from "@/components/post/post-card";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getPosts, getTags } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { parsePage } from "@/lib/parse-page";

export const metadata: Metadata = pageMetadata({
  title: "标签",
  description: "按标签浏览文章",
  path: "/tags",
});

export default async function TagsPage({
  searchParams,
}: {
  searchParams: Promise<{ tag?: string; page?: string }>;
}) {
  const { tag, page: rawPage } = await searchParams;

  if (!tag) {
    const tags = await getTags();

    return (
      <section className="shell">
        <PageHeader
          title="标签"
          description={`按标签浏览文章，共 ${tags.items.length} 个标签。`}
        />

        {tags.items.length === 0 ? (
          <div className="glass empty-state">暂无标签。</div>
        ) : (
          <div className="tag-cloud-page">
            {tags.items.map((item) => (
              <Link
                key={item.name}
                href={`/tags?tag=${encodeURIComponent(item.name)}`}
                className="chip"
              >
                #{item.name}
                <span className="tag-count">{item.count}</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    );
  }

  const page = parsePage(rawPage);
  const data = await getPosts({ tag, page });

  return (
    <section className="shell">
      <PageHeader
        title={`标签：${tag}`}
        description={`共 ${data.meta.total} 篇相关文章。`}
      />

      {data.items.length === 0 ? (
        <div className="glass empty-state">
          <p>没有更多文章</p>
          <Link href="/tags">返回标签列表</Link>
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
        buildHref={(target) => {
          const base = `/tags?tag=${encodeURIComponent(tag)}`;
          return target <= 1 ? base : `${base}&page=${target}`;
        }}
      />
    </section>
  );
}
