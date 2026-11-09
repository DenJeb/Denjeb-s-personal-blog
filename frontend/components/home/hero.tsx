import Image from "next/image";
import Link from "next/link";

import type { components } from "@/lib/api/schema";
import { siteConfig } from "@/lib/site-config";

type SiteInfo = components["schemas"]["SiteInfo"];

export function Hero({
  site,
  stats,
}: {
  site: SiteInfo;
  stats: { posts: number; tags: number; moments: number };
}) {
  return (
    <section className="hero">
      <div>
        <p className="hero-kicker">
          <span className="pulse" aria-hidden="true" />
          持续更新ing...
        </p>
        <h1 className="hero-title">{site.app_name}</h1>
        <p className="hero-tagline hero-terminal">
          <span className="hero-terminal-line">
            <span className="hero-terminal-prompt" aria-hidden="true">
              ❯
            </span>
            <span className="hero-terminal-command">
              echo &quot;欢迎来到我的个人博客&quot;
            </span>
            <span className="hero-terminal-caret" aria-hidden="true" />
          </span>
          <span className="hero-terminal-line hero-terminal-note">
            <span className="hero-terminal-prompt" aria-hidden="true">
              #
            </span>
            大学生 / 计算机科学与技术 · 记录学习、开发与生活
          </span>
        </p>

        <div className="hero-actions">
          <Link href="/posts" className="btn btn-primary">
            阅读文章
          </Link>
          <Link href="/about" className="btn btn-primary">
            关于我
          </Link>
        </div>

        <div className="hero-stats">
          <div className="stat">
            <span className="stat-value">{stats.posts}</span>
            <span className="stat-label">篇文章</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.tags}</span>
            <span className="stat-label">个标签</span>
          </div>
          <div className="stat">
            <span className="stat-value">{stats.moments}</span>
            <span className="stat-label">条动态</span>
          </div>
        </div>
      </div>

      <aside className="glass profile-card">
        <div className="profile-top">
          <div className="avatar" aria-hidden="true">
            <Image
              className="avatar-photo"
              src="/avatar.jpg"
              alt=""
              width={72}
              height={72}
              priority
            />
          </div>
          <div>
            <div className="profile-name">{site.author}</div>
            <div className="profile-role">大学生 / 计算机科学与技术</div>
          </div>
        </div>

        <p className="profile-bio">
          喜欢游戏、摄影、音乐、电影、篮球、羽毛球、乒乓球、旅游，也喜欢记录生活、想法和一些不想忘掉的瞬间。
        </p>

        <div className="profile-links">
          <a
            className="btn btn-ghost"
            href={siteConfig.github}
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <a className="btn btn-ghost" href={`mailto:${siteConfig.email}`}>
            邮箱
          </a>
        </div>
      </aside>
    </section>
  );
}
