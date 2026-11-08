import type { Metadata } from "next";

import { MomentCard } from "@/components/moments/moment-card";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getCurrentUser, getMoments } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { parsePage } from "@/lib/parse-page";

export const metadata: Metadata = pageMetadata({
  title: "动态",
  description: "零碎的想法和日常",
  path: "/moments",
});

export default async function MomentsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);
  const [data, user] = await Promise.all([
    getMoments(page),
    getCurrentUser(),
  ]);

  return (
    <section className="shell">
      <PageHeader
        title="动态"
        description="零碎的想法、日常和一些还没写成文章的记录。"
      />

      {data.items.length === 0 ? (
        <div className="glass empty-state">暂无动态。</div>
      ) : (
        <div className="timeline">
          {data.items.map((moment) => (
            <div
              key={moment.id}
              id={`moment-${moment.id}`}
              className="timeline-item"
            >
              <MomentCard moment={moment} isLoggedIn={Boolean(user)} />
            </div>
          ))}
        </div>
      )}

      <Pagination
        page={data.meta.page}
        totalPages={data.meta.total_pages}
        hasPrev={data.meta.has_prev}
        hasNext={data.meta.has_next}
        buildHref={(target) =>
          target <= 1 ? "/moments" : `/moments?page=${target}`
        }
      />
    </section>
  );
}
