import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/ui/page-header";
import { getArchive } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = pageMetadata({
  title: "归档",
  description: "按时间归档的文章",
  path: "/archive",
});

export default async function ArchivePage() {
  const archive = await getArchive();

  return (
    <section className="shell">
      <PageHeader
        title="归档"
        description={`共 ${archive.total} 篇文章，按时间排列。`}
      />

      {archive.total === 0 ? (
        <div className="glass empty-state">暂无文章。</div>
      ) : (
        <div className="archive">
          {archive.years.map((year) => (
            <section key={year.year}>
              <h2 className="archive-year">{year.year}</h2>

              {year.months.map((month) => (
                <div key={month.month} className="archive-month">
                  <h3 className="archive-month-title">{month.month} 月</h3>
                  <div className="archive-list">
                    {month.posts.map((post) => (
                      <Link
                        key={post.id}
                        href={`/posts/${post.slug}`}
                        className="archive-item"
                      >
                        <span>{post.title}</span>
                        <span className="archive-date">
                          {post.published_at}
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
