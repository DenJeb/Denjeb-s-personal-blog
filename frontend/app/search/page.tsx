import type { Metadata } from "next";

import { PostCard } from "@/components/post/post-card";
import { SearchForm } from "@/components/search/search-form";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getSearch } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { parsePage } from "@/lib/parse-page";
import { firstParam } from "@/lib/search-params";

export const metadata: Metadata = pageMetadata({
  title: "搜索",
  description: "搜索文章",
  path: "/search",
});

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[]; page?: string | string[] }>;
}) {
  const { q: rawQ, page: rawPage } = await searchParams;
  const query = (firstParam(rawQ) ?? "").trim();
  const page = parsePage(firstParam(rawPage));
  const tooLong = query.length > 100;
  const results = query && !tooLong ? await getSearch(query, page) : null;

  return (
    <section className="shell">
      <PageHeader title="搜索" description="按标题、摘要和正文搜索文章。" />

      <div className="glass search-panel">
        <SearchForm defaultValue={firstParam(rawQ) ?? ""} />
      </div>

      {!query ? (
        <p className="search-hint">输入关键词开始搜索</p>
      ) : tooLong ? (
        <p className="search-hint">搜索词不能超过 100 个字符</p>
      ) : results && results.items.length === 0 ? (
        <p className="search-hint">没有找到相关文章</p>
      ) : results ? (
        <div className="post-grid">
          {results.items.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      ) : null}

      {results ? (
        <Pagination
          page={results.meta.page}
          totalPages={results.meta.total_pages}
          hasPrev={results.meta.has_prev}
          hasNext={results.meta.has_next}
          buildHref={(target) => {
            const base = `/search?q=${encodeURIComponent(query)}`;
            return target <= 1 ? base : `${base}&page=${target}`;
          }}
        />
      ) : null}
    </section>
  );
}
