import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import { CommentList } from "@/components/comments/comment-list";
import { PostBody } from "@/components/post/post-body";
import { RelatedPosts } from "@/components/post/related-posts";
import { Toc } from "@/components/post/toc";
import { Pagination } from "@/components/ui/pagination";
import { getPost, getPostComments } from "@/lib/api/fetchers";
import { parsePage } from "@/lib/parse-page";
import { siteConfig } from "@/lib/site-config";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);

  if (!post) {
    return { title: "文章不存在" };
  }

  return {
    title: post.title,
    description: post.summary,
    alternates: {
      canonical: `/posts/${post.slug}`,
      types: { "application/rss+xml": "/rss.xml" },
    },
    openGraph: {
      type: "article",
      title: post.title,
      description: post.summary,
      url: `/posts/${post.slug}`,
      publishedTime: post.published_at,
      tags: post.tags,
    },
    twitter: {
      card: "summary",
      title: post.title,
      description: post.summary,
    },
  };
}

export default async function PostPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ comment_page?: string }>;
}) {
  const { slug } = await params;
  const { comment_page: rawCommentPage } = await searchParams;

  const post = await getPost(slug);
  if (!post) {
    notFound();
  }

  if (post.slug !== slug) {
    permanentRedirect(`/posts/${post.slug}`);
  }

  const commentPage = parsePage(rawCommentPage);
  const comments = await getPostComments(post.slug, commentPage);
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.summary,
    datePublished: post.published_at,
    dateModified: post.published_at,
    author: { "@type": "Person", name: siteConfig.author },
    mainEntityOfPage: `${siteConfig.url}/posts/${post.slug}`,
    keywords: post.tags.join(", "),
  };

  return (
    <div className="shell article-shell">
      <Link href="/posts" className="back-link">
        ← 返回文章列表
      </Link>

      <header className="article-header">
        {post.tags.length > 0 ? (
          <div className="tag-cloud">
            {post.tags.map((tag) => (
              <Link
                key={tag}
                href={`/tags?tag=${encodeURIComponent(tag)}`}
                className="chip"
              >
                #{tag}
              </Link>
            ))}
          </div>
        ) : null}

        <h1 className="article-title">{post.title}</h1>
        {post.summary ? <p className="article-summary">{post.summary}</p> : null}

        <div className="article-meta">
          <time dateTime={post.published_at}>{post.published_at}</time>
          <span>{post.reading_minutes} 分钟</span>
          <span>{siteConfig.author}</span>
        </div>
      </header>

      <div className="article-toc-mobile">
        <Toc items={post.toc} />
      </div>

      <div className="article-layout">
        <article className="glass article-panel">
          <script
            type="application/ld+json"
            nonce={nonce}
            dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
          />

          <PostBody html={post.content_html} />

          {post.previous_post || post.next_post ? (
            <nav aria-label="上下篇" className="post-nav">
              {post.previous_post ? (
                <Link
                  href={`/posts/${post.previous_post.slug}`}
                  className="post-nav-card"
                >
                  <div className="post-nav-label">上一篇</div>
                  <div className="post-nav-title">
                    {post.previous_post.title}
                  </div>
                </Link>
              ) : null}
              {post.next_post ? (
                <Link
                  href={`/posts/${post.next_post.slug}`}
                  className="post-nav-card"
                >
                  <div className="post-nav-label">下一篇</div>
                  <div className="post-nav-title">{post.next_post.title}</div>
                </Link>
              ) : null}
            </nav>
          ) : null}

          <section id="comments" className="comments-section">
            <h2 className="comments-title">
              评论{comments.meta.total > 0 ? `（${comments.meta.total}）` : ""}
            </h2>
            <CommentList comments={comments.items} />
            <Pagination
              page={comments.meta.page}
              totalPages={comments.meta.total_pages}
              hasPrev={comments.meta.has_prev}
              hasNext={comments.meta.has_next}
              buildHref={(target) =>
                target <= 1
                  ? `/posts/${post.slug}#comments`
                  : `/posts/${post.slug}?comment_page=${target}#comments`
              }
            />
          </section>
        </article>

        <aside className="article-side">
          <div className="article-toc-desktop">
            <Toc items={post.toc} />
          </div>

          {post.tags.length > 0 ? (
            <section className="glass side-card">
              <h2 className="side-title">标签</h2>
              <div className="tag-cloud">
                {post.tags.map((tag) => (
                  <Link
                    key={tag}
                    href={`/tags?tag=${encodeURIComponent(tag)}`}
                    className="chip"
                  >
                    #{tag}
                  </Link>
                ))}
              </div>
            </section>
          ) : null}

          <RelatedPosts posts={post.related_posts} />
        </aside>
      </div>
    </div>
  );
}
