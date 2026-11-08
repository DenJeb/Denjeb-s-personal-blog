import type { Metadata } from "next";

import { WriteForm } from "@/components/forms/write-form";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getCurrentUser, getGuestbook } from "@/lib/api/fetchers";
import { pageMetadata } from "@/lib/page-metadata";
import { parsePage } from "@/lib/parse-page";

export const metadata: Metadata = pageMetadata({
  title: "留言",
  description: "留言板",
  path: "/guestbook",
});

export default async function GuestbookPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);
  const [data, user] = await Promise.all([
    getGuestbook(page),
    getCurrentUser(),
  ]);

  return (
    <section className="shell">
      <PageHeader title="留言" description="想说的话，留在这里。" />

      <div className="glass guestbook-compose">
        <WriteForm
          endpoint="/api/v1/guestbook"
          maxLength={1000}
          isLoggedIn={Boolean(user)}
          nextPath="/guestbook"
          placeholder="写下想说的话…"
          buttonLabel="提交留言"
          loginPrompt="登录后留言"
        />
      </div>

      {data.items.length === 0 ? (
        <div className="glass empty-state">暂无留言。</div>
      ) : (
        <div className="guestbook-list">
          {data.items.map((message) => (
            <article key={message.id} className="glass glass-hover guestbook-card">
              <div className="guestbook-author">{message.author_name}</div>
              <div className="guestbook-text">{message.content}</div>
              <time className="guestbook-time" dateTime={message.created_at}>
                {message.created_at}
              </time>
            </article>
          ))}
        </div>
      )}

      <Pagination
        page={data.meta.page}
        totalPages={data.meta.total_pages}
        hasPrev={data.meta.has_prev}
        hasNext={data.meta.has_next}
        buildHref={(target) =>
          target <= 1 ? "/guestbook" : `/guestbook?page=${target}`
        }
      />
    </section>
  );
}
