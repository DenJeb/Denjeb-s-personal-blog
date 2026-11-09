import type { Metadata } from "next";
import Link from "next/link";

import { Hero } from "@/components/home/hero";
import { MomentPreview } from "@/components/home/moment-preview";
import { TagCloud } from "@/components/home/tag-cloud";
import { PostCard } from "@/components/post/post-card";
import {
  getMoments,
  getPosts,
  getSiteInfo,
  getTags,
} from "@/lib/api/fetchers";
import { loadSiteInfo } from "@/lib/api/load-site-info";

export const metadata: Metadata = {
  alternates: {
    canonical: "/",
    types: { "application/rss+xml": "/rss.xml" },
  },
};

export default async function Home() {
  const site = await loadSiteInfo(getSiteInfo);
  const [postsPage, tags, moments] = await Promise.all([
    getPosts({ perPage: 3 }).catch(() => null),
    getTags().catch(() => null),
    getMoments(1).catch(() => null),
  ]);

  const posts = postsPage?.items ?? [];
  const stats = {
    posts: postsPage?.meta.total ?? 0,
    tags: tags?.items.length ?? 0,
    moments: moments?.meta.total ?? 0,
  };

  return (
    <div className="shell">
      <Hero site={site} stats={stats} />

      <div className="home-layout">
        <section className="home-feed">
          <div className="section-head">
            <h2 className="section-title">最近文章</h2>
            <Link className="section-link" href="/posts">
              查看全部
            </Link>
          </div>

          {posts.length === 0 ? (
            <div className="glass empty-state">还没有文章，去写第一篇吧。</div>
          ) : (
            <div className="post-grid">
              {posts.map((post, index) => (
                <PostCard key={post.id} post={post} featured={index === 0} />
              ))}
            </div>
          )}
        </section>

        <aside className="home-side">
          <section className="glass side-card">
            <h2 className="side-title">标签</h2>
            <TagCloud tags={tags?.items ?? []} />
          </section>

          <section className="glass side-card">
            <h2 className="side-title">最近动态</h2>
            <MomentPreview moments={moments?.items.slice(0, 3) ?? []} />
            <Link className="section-link" href="/moments">
              查看全部动态
            </Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
