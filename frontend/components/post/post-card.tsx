import Link from "next/link";

import type { components } from "@/lib/api/schema";

type PostSummary = components["schemas"]["PostSummary"];

export function PostCard({
  post,
  featured = false,
}: {
  post: PostSummary;
  featured?: boolean;
}) {
  return (
    <article
      className={`post-card glass glass-hover ${
        featured ? "post-card-featured" : ""
      }`}
    >
      <div className="post-card-meta">
        <time dateTime={post.published_at}>{post.published_at}</time>
        <span>{post.reading_minutes} 分钟</span>
      </div>

      <h2 className="post-card-title">
        <Link href={`/posts/${post.slug}`}>{post.title}</Link>
      </h2>

      {post.summary ? <p className="post-card-summary">{post.summary}</p> : null}

      <div className="post-tags">
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
    </article>
  );
}
