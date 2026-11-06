import Link from "next/link";

import type { components } from "@/lib/api/schema";

type PostSummary = components["schemas"]["PostSummary"];

export function RelatedPosts({ posts }: { posts: PostSummary[] }) {
  if (posts.length === 0) {
    return null;
  }

  return (
    <section className="glass side-card">
      <h2 className="side-title">相关文章</h2>
      <div className="related-list">
        {posts.map((post) => (
          <Link
            key={post.id}
            href={`/posts/${post.slug}`}
            className="related-item"
          >
            <span className="related-title">{post.title}</span>
            <span className="related-date">{post.published_at}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
